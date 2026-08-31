"""Información exógena: agrupación, umbral en UVT, totales de control y re-descarga."""

from __future__ import annotations

from decimal import Decimal
from xml.etree import ElementTree as ET

import pytest

from app.models import Tercero
from app.services import uvt

UVT_2025 = Decimal("49799.00")


@pytest.fixture()
def uvt_sincronizada(db):
    uvt.sincronizar(db, 2025, proveedor=uvt.ProveedorUvtSimulado())


@pytest.fixture()
def otro_tercero(db, empresa):
    registro = Tercero(
        empresa_id=empresa.id, tipo_doc="NIT", num_doc="830053105", dv="3", nombre="Cliente Menor S.A.S."
    )
    db.add(registro)
    db.flush()
    return registro


@pytest.fixture()
def registrar(client, empresa):
    def _registrar(lineas, fecha="2025-03-10", descripcion="Movimiento"):
        borrador = client.post(
            f"/api/empresas/{empresa.id}/comprobantes",
            json={"fecha": fecha, "descripcion": descripcion, "lineas": lineas},
        )
        assert borrador.status_code == 201, borrador.text
        contabilizado = client.post(f"/api/comprobantes/{borrador.json()['id']}/contabilizar")
        assert contabilizado.status_code == 200, contabilizado.text
        return contabilizado.json()

    return _registrar


def _generar(client, empresa_id, umbral_uvt="0.00", anio=2025):
    return client.post(
        "/api/exogena/generar",
        json={"empresa_id": empresa_id, "anio_gravable": anio, "umbral_uvt": umbral_uvt},
    )


def _parsear(respuesta):
    return ET.fromstring(respuesta.content)


def test_estructura_del_xml_sigue_el_formato_del_enunciado(
    client, empresa, cuentas, tercero, registrar, uvt_sincronizada
):
    registrar(
        [
            {"cuenta_id": cuentas["5105"].id, "debito": "1000000.00", "credito": "0.00",
             "tercero_id": tercero.id},
            {"cuenta_id": cuentas["2205"].id, "debito": "0.00", "credito": "1000000.00",
             "tercero_id": tercero.id},
        ]
    )

    respuesta = _generar(client, empresa.id)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["content-type"].startswith("application/xml")
    assert "attachment" in respuesta.headers["content-disposition"]

    raiz = _parsear(respuesta)
    assert raiz.tag == "InformacionExogena"
    assert raiz.attrib["version"] == "1.0"

    informante = raiz.find("Informante")
    assert informante.attrib["nit"] == empresa.nit
    assert informante.attrib["dv"] == empresa.dv
    assert informante.attrib["razonSocial"] == empresa.razon_social
    assert informante.attrib["anioGravable"] == "2025"

    registro = raiz.find("Registros/Registro")
    assert set(registro.attrib) == {
        "tipoDoc", "numDoc", "nombre", "concepto", "valorBruto", "valorRetencion"
    }

    assert raiz.find("Totales") is not None


def test_movimientos_se_agrupan_por_tercero_y_concepto(
    client, empresa, cuentas, tercero, registrar, uvt_sincronizada
):
    # Dos gastos (mismo concepto 5001) y un ingreso (concepto 1007) del mismo tercero.
    for monto in ("1000000.00", "500000.00"):
        registrar(
            [
                {"cuenta_id": cuentas["5105"].id, "debito": monto, "credito": "0.00",
                 "tercero_id": tercero.id},
                {"cuenta_id": cuentas["2205"].id, "debito": "0.00", "credito": monto,
                 "tercero_id": tercero.id},
            ]
        )
    registrar(
        [
            {"cuenta_id": cuentas["1105"].id, "debito": "700000.00", "credito": "0.00"},
            {"cuenta_id": cuentas["4135"].id, "debito": "0.00", "credito": "700000.00",
             "tercero_id": tercero.id},
        ]
    )

    raiz = _parsear(_generar(client, empresa.id))
    registros = raiz.findall("Registros/Registro")
    por_concepto = {r.attrib["concepto"]: r for r in registros}

    # Los dos gastos se consolidan en un único registro de concepto 5001.
    assert por_concepto["5001"].attrib["valorBruto"] == "1500000.00"
    assert por_concepto["1007"].attrib["valorBruto"] == "700000.00"
    # El tercero es el mismo, pero los conceptos no se mezclan.
    assert {r.attrib["numDoc"] for r in registros} == {tercero.num_doc}


def test_totales_de_control_cuadran_con_los_registros_incluidos(
    client, empresa, cuentas, tercero, otro_tercero, registrar, uvt_sincronizada
):
    registrar(
        [
            {"cuenta_id": cuentas["5105"].id, "debito": "1000000.00", "credito": "0.00",
             "tercero_id": tercero.id},
            {"cuenta_id": cuentas["2205"].id, "debito": "0.00", "credito": "1000000.00",
             "tercero_id": otro_tercero.id},
        ]
    )

    raiz = _parsear(_generar(client, empresa.id))
    registros = raiz.findall("Registros/Registro")
    totales = raiz.find("Totales")

    suma = sum(Decimal(r.attrib["valorBruto"]) for r in registros)
    assert totales.attrib["registros"] == str(len(registros))
    assert Decimal(totales.attrib["totalValorBruto"]) == suma


def test_umbral_en_uvt_excluye_terceros_menores_con_trazabilidad(
    client, empresa, cuentas, tercero, otro_tercero, registrar, uvt_sincronizada
):
    # 100 UVT de 2025 = 4.979.900 pesos.
    registrar(
        [
            {"cuenta_id": cuentas["5105"].id, "debito": "10000000.00", "credito": "0.00",
             "tercero_id": tercero.id},
            {"cuenta_id": cuentas["2205"].id, "debito": "0.00", "credito": "10000000.00"},
        ]
    )
    registrar(
        [
            {"cuenta_id": cuentas["5105"].id, "debito": "100000.00", "credito": "0.00",
             "tercero_id": otro_tercero.id},
            {"cuenta_id": cuentas["2205"].id, "debito": "0.00", "credito": "100000.00"},
        ]
    )

    respuesta = _generar(client, empresa.id, umbral_uvt="100.00")
    raiz = _parsear(respuesta)
    incluidos = {r.attrib["numDoc"] for r in raiz.findall("Registros/Registro")}
    assert incluidos == {tercero.num_doc}

    historial = client.get("/api/exogena/historial", params={"empresa_id": empresa.id}).json()
    generacion = historial[0]
    esperado = (Decimal("100.00") * UVT_2025).quantize(Decimal("0.01"))
    assert generacion["umbral_pesos"] == format(esperado, "f")
    # La exclusión queda registrada con su motivo, no se pierde silenciosamente.
    assert len(generacion["exclusiones"]) == 1
    exclusion = generacion["exclusiones"][0]
    assert otro_tercero.num_doc in exclusion["tercero"]
    assert "umbral" in exclusion["motivo"]


def test_tercero_con_dv_invalido_se_excluye_con_motivo(
    client, db, empresa, cuentas, registrar, uvt_sincronizada
):
    invalido = Tercero(
        empresa_id=empresa.id, tipo_doc="NIT", num_doc="900123456", dv="1", nombre="Datos Erróneos S.A.S."
    )
    db.add(invalido)
    db.flush()

    registrar(
        [
            {"cuenta_id": cuentas["5105"].id, "debito": "5000000.00", "credito": "0.00",
             "tercero_id": invalido.id},
            {"cuenta_id": cuentas["2205"].id, "debito": "0.00", "credito": "5000000.00"},
        ]
    )

    _generar(client, empresa.id)
    generacion = client.get("/api/exogena/historial").json()[0]
    assert generacion["total_registros"] == 0
    assert "dígito de verificación" in generacion["exclusiones"][0]["motivo"]


def test_informante_con_dv_invalido_aborta_la_generacion(client, db, empresa, uvt_sincronizada):
    empresa.dv = "1"  # el DV correcto de 900123456 es 8
    db.flush()

    respuesta = _generar(client, empresa.id)
    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "NIT_DV_INVALIDO"


def test_sin_uvt_del_anio_la_generacion_falla_indicando_como_resolverlo(client, empresa):
    respuesta = _generar(client, empresa.id)
    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "UVT_NO_DISPONIBLE"


def test_borradores_y_movimientos_sin_tercero_no_se_reportan(
    client, empresa, cuentas, tercero, registrar, uvt_sincronizada
):
    # Movimiento sin tercero: no es reportable en exógena.
    registrar(
        [
            {"cuenta_id": cuentas["5105"].id, "debito": "800000.00", "credito": "0.00"},
            {"cuenta_id": cuentas["2205"].id, "debito": "0.00", "credito": "800000.00"},
        ]
    )
    # Borrador con tercero: aún no es un hecho contable.
    client.post(
        f"/api/empresas/{empresa.id}/comprobantes",
        json={
            "fecha": "2025-03-10",
            "descripcion": "Borrador",
            "lineas": [
                {"cuenta_id": cuentas["5105"].id, "debito": "900000.00", "credito": "0.00",
                 "tercero_id": tercero.id},
                {"cuenta_id": cuentas["2205"].id, "debito": "0.00", "credito": "900000.00"},
            ],
        },
    )

    raiz = _parsear(_generar(client, empresa.id))
    assert raiz.findall("Registros/Registro") == []
    assert raiz.find("Totales").attrib["totalValorBruto"] == "0.00"


def test_movimientos_de_otro_anio_gravable_no_entran(
    client, empresa, cuentas, tercero, registrar, uvt_sincronizada
):
    registrar(
        [
            {"cuenta_id": cuentas["5105"].id, "debito": "1000000.00", "credito": "0.00",
             "tercero_id": tercero.id},
            {"cuenta_id": cuentas["2205"].id, "debito": "0.00", "credito": "1000000.00"},
        ],
        fecha="2026-03-10",
    )

    raiz = _parsear(_generar(client, empresa.id, anio=2025))
    assert raiz.findall("Registros/Registro") == []


def test_retencion_se_informa_aparte_del_valor_bruto(
    client, empresa, cuentas, tercero, registrar, uvt_sincronizada
):
    registrar(
        [
            {"cuenta_id": cuentas["5105"].id, "debito": "1000000.00", "credito": "0.00",
             "tercero_id": tercero.id},
            {"cuenta_id": cuentas["2365"].id, "debito": "0.00", "credito": "25000.00",
             "tercero_id": tercero.id},
            {"cuenta_id": cuentas["2205"].id, "debito": "0.00", "credito": "975000.00"},
        ]
    )

    raiz = _parsear(_generar(client, empresa.id))
    registro = raiz.find("Registros/Registro")
    # La retención no infla el valor bruto: va en su propio atributo.
    assert registro.attrib["valorBruto"] == "1000000.00"
    assert registro.attrib["valorRetencion"] == "25000.00"


def test_historial_permite_redescargar_el_mismo_archivo(
    client, empresa, cuentas, tercero, registrar, uvt_sincronizada
):
    registrar(
        [
            {"cuenta_id": cuentas["5105"].id, "debito": "1000000.00", "credito": "0.00",
             "tercero_id": tercero.id},
            {"cuenta_id": cuentas["2205"].id, "debito": "0.00", "credito": "1000000.00"},
        ]
    )
    original = _generar(client, empresa.id)
    generacion_id = original.headers["X-Generacion-Id"]

    redescarga = client.get(f"/api/exogena/historial/{generacion_id}/archivo")
    assert redescarga.status_code == 200
    # Byte a byte idéntico: el archivo se conserva, no se regenera.
    assert redescarga.content == original.content


def test_redescarga_de_generacion_inexistente_es_404(client):
    assert client.get("/api/exogena/historial/9999/archivo").status_code == 404
