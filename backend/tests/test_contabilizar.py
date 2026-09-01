"""Reglas de contabilización — el núcleo del motor (escenarios 1, 2, 4 y 6 del enunciado).

Se prueban vía API para cubrir también el contrato HTTP (códigos de error y montos como string).
"""

from __future__ import annotations

import pytest


def _crear_borrador(client, empresa_id, lineas, fecha="2025-01-15", descripcion="Compra de insumos"):
    return client.post(
        f"/api/empresas/{empresa_id}/comprobantes",
        json={"fecha": fecha, "descripcion": descripcion, "lineas": lineas},
    )


@pytest.fixture()
def compra_valida(cuentas, tercero):
    """Escenario 1: gasto 1.000.000 + IVA 190.000 contra proveedores 1.190.000."""
    return [
        {"cuenta_id": cuentas["5105"].id, "debito": "1000000.00", "credito": "0.00"},
        {"cuenta_id": cuentas["2408"].id, "debito": "190000.00", "credito": "0.00"},
        {
            "cuenta_id": cuentas["2205"].id,
            "debito": "0.00",
            "credito": "1190000.00",
            "tercero_id": tercero.id,
        },
    ]


def test_escenario_1_comprobante_valido_se_contabiliza(client, empresa, compra_valida):
    borrador = _crear_borrador(client, empresa.id, compra_valida)
    assert borrador.status_code == 201, borrador.text
    assert borrador.json()["estado"] == "borrador"
    assert borrador.json()["numero"] is None

    respuesta = client.post(f"/api/comprobantes/{borrador.json()['id']}/contabilizar")
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "contabilizado"
    assert cuerpo["numero"] == 1
    # Los montos viajan como string exacto, nunca como número JSON.
    assert cuerpo["total_debito"] == "1190000.00"
    assert cuerpo["total_credito"] == "1190000.00"


def test_escenario_2_desbalanceado_se_rechaza_con_causa(client, empresa, cuentas):
    borrador = _crear_borrador(
        client,
        empresa.id,
        [
            {"cuenta_id": cuentas["1105"].id, "debito": "500000.00", "credito": "0.00"},
            {"cuenta_id": cuentas["4135"].id, "debito": "0.00", "credito": "450000.00"},
        ],
    )
    respuesta = client.post(f"/api/comprobantes/{borrador.json()['id']}/contabilizar")
    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "PARTIDA_DOBLE"
    # El mensaje debe indicar la causa concreta, no un error genérico.
    assert "500000.00" in respuesta.json()["detail"]


def test_escenario_4_periodo_cerrado_rechaza_contabilizacion(client, empresa, compra_valida):
    borrador = _crear_borrador(client, empresa.id, compra_valida)
    periodos = client.get(f"/api/empresas/{empresa.id}/periodos").json()
    enero = next(p for p in periodos if (p["anio"], p["mes"]) == (2025, 1))

    assert client.post(f"/api/periodos/{enero['id']}/cerrar").status_code == 200

    respuesta = client.post(f"/api/comprobantes/{borrador.json()['id']}/contabilizar")
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "PERIODO_CERRADO"


def test_periodo_cerrado_rechaza_nuevos_borradores(client, empresa, compra_valida):
    periodos = client.get(f"/api/empresas/{empresa.id}/periodos").json()
    enero = next(p for p in periodos if (p["anio"], p["mes"]) == (2025, 1))
    client.post(f"/api/periodos/{enero['id']}/cerrar")

    respuesta = _crear_borrador(client, empresa.id, compra_valida)
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "PERIODO_CERRADO"


def test_menos_de_dos_lineas_se_rechaza(client, empresa, cuentas):
    borrador = _crear_borrador(
        client,
        empresa.id,
        [{"cuenta_id": cuentas["1105"].id, "debito": "1000.00", "credito": "0.00"}],
    )
    respuesta = client.post(f"/api/comprobantes/{borrador.json()['id']}/contabilizar")
    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "LINEAS_INSUFICIENTES"


def test_linea_con_debito_y_credito_se_rechaza(client, empresa, cuentas):
    borrador = _crear_borrador(
        client,
        empresa.id,
        [
            {"cuenta_id": cuentas["1105"].id, "debito": "1000.00", "credito": "1000.00"},
            {"cuenta_id": cuentas["4135"].id, "debito": "0.00", "credito": "1000.00"},
        ],
    )
    respuesta = client.post(f"/api/comprobantes/{borrador.json()['id']}/contabilizar")
    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "DEBITO_Y_CREDITO"


def test_cuenta_inactiva_se_rechaza(client, empresa, cuentas, compra_valida):
    borrador = _crear_borrador(client, empresa.id, compra_valida)
    client.patch(f"/api/empresas/{empresa.id}/cuentas/{cuentas['2408'].id}", json={"activa": False})

    respuesta = client.post(f"/api/comprobantes/{borrador.json()['id']}/contabilizar")
    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "CUENTA_INACTIVA"
    assert "2408" in respuesta.json()["detail"]


def test_valores_con_decimales_excesivos_se_rechazan_en_el_borde(client, empresa, cuentas):
    respuesta = _crear_borrador(
        client,
        empresa.id,
        [
            {"cuenta_id": cuentas["1105"].id, "debito": "1000.123", "credito": "0.00"},
            {"cuenta_id": cuentas["4135"].id, "debito": "0.00", "credito": "1000.123"},
        ],
    )
    # Se rechaza en la validación del esquema, antes de tocar la base de datos.
    assert respuesta.status_code == 422


def test_numeracion_es_consecutiva_por_periodo(client, empresa, compra_valida):
    numeros = []
    for _ in range(3):
        borrador = _crear_borrador(client, empresa.id, compra_valida)
        contabilizado = client.post(f"/api/comprobantes/{borrador.json()['id']}/contabilizar")
        numeros.append(contabilizado.json()["numero"])
    assert numeros == [1, 2, 3]


def test_comprobante_contabilizado_no_se_puede_modificar(client, empresa, compra_valida):
    borrador = _crear_borrador(client, empresa.id, compra_valida)
    comprobante_id = borrador.json()["id"]
    client.post(f"/api/comprobantes/{comprobante_id}/contabilizar")

    respuesta = client.put(
        f"/api/comprobantes/{comprobante_id}",
        json={"descripcion": "Intento de alteración"},
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "COMPROBANTE_PROTEGIDO"


def test_contabilizacion_fallida_no_deja_estado_parcial(client, db, empresa, cuentas):
    """Consistencia ante fallos parciales: si la validación falla, no se asigna número."""
    borrador = _crear_borrador(
        client,
        empresa.id,
        [
            {"cuenta_id": cuentas["1105"].id, "debito": "500000.00", "credito": "0.00"},
            {"cuenta_id": cuentas["4135"].id, "debito": "0.00", "credito": "450000.00"},
        ],
    )
    comprobante_id = borrador.json()["id"]
    client.post(f"/api/comprobantes/{comprobante_id}/contabilizar")

    estado = client.get(f"/api/comprobantes/{comprobante_id}").json()
    assert estado["estado"] == "borrador"
    assert estado["numero"] is None
