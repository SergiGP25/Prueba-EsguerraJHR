"""Libro mayor: qué movimientos entran y cómo se acumula el saldo."""

from __future__ import annotations

import pytest


@pytest.fixture()
def registrar(client, empresa):
    def _registrar(lineas, fecha="2025-01-15", descripcion="Movimiento", contabilizar=True):
        borrador = client.post(
            f"/api/empresas/{empresa.id}/comprobantes",
            json={"fecha": fecha, "descripcion": descripcion, "lineas": lineas},
        )
        assert borrador.status_code == 201, borrador.text
        if not contabilizar:
            return borrador.json()
        contabilizado = client.post(f"/api/comprobantes/{borrador.json()['id']}/contabilizar")
        assert contabilizado.status_code == 200, contabilizado.text
        return contabilizado.json()

    return _registrar


def _consultar(client, empresa_id, cuenta_id, desde="2025-01-01", hasta="2025-01-31"):
    return client.get(
        f"/api/empresas/{empresa_id}/libro-mayor",
        params={"cuenta_id": cuenta_id, "fecha_desde": desde, "fecha_hasta": hasta},
    )


def test_saldo_acumulado_en_cuenta_de_naturaleza_debito(client, empresa, cuentas, registrar):
    caja = cuentas["1105"]
    registrar(
        [
            {"cuenta_id": caja.id, "debito": "500000.00", "credito": "0.00"},
            {"cuenta_id": cuentas["4135"].id, "debito": "0.00", "credito": "500000.00"},
        ],
        fecha="2025-01-10",
    )
    registrar(
        [
            {"cuenta_id": cuentas["5105"].id, "debito": "200000.00", "credito": "0.00"},
            {"cuenta_id": caja.id, "debito": "0.00", "credito": "200000.00"},
        ],
        fecha="2025-01-20",
    )

    cuerpo = _consultar(client, empresa.id, caja.id).json()
    saldos = [m["saldo"] for m in cuerpo["movimientos"]]
    # Naturaleza débito: el saldo sube con débitos y baja con créditos.
    assert saldos == ["500000.00", "300000.00"]
    assert cuerpo["saldo_final"] == "300000.00"
    assert cuerpo["total_debito"] == "500000.00"
    assert cuerpo["total_credito"] == "200000.00"


def test_saldo_acumulado_en_cuenta_de_naturaleza_credito(client, empresa, cuentas, registrar):
    ingresos = cuentas["4135"]
    registrar(
        [
            {"cuenta_id": cuentas["1105"].id, "debito": "500000.00", "credito": "0.00"},
            {"cuenta_id": ingresos.id, "debito": "0.00", "credito": "500000.00"},
        ],
    )

    cuerpo = _consultar(client, empresa.id, ingresos.id).json()
    # Naturaleza crédito: un crédito aumenta el saldo (se lee en positivo).
    assert cuerpo["movimientos"][0]["saldo"] == "500000.00"
    assert cuerpo["saldo_final"] == "500000.00"


def test_borradores_no_aparecen_en_el_mayor(client, empresa, cuentas, registrar):
    caja = cuentas["1105"]
    registrar(
        [
            {"cuenta_id": caja.id, "debito": "999999.00", "credito": "0.00"},
            {"cuenta_id": cuentas["4135"].id, "debito": "0.00", "credito": "999999.00"},
        ],
        contabilizar=False,
    )

    cuerpo = _consultar(client, empresa.id, caja.id).json()
    assert cuerpo["movimientos"] == []
    assert cuerpo["saldo_final"] == "0.00"


def test_reversion_deja_saldo_neto_en_cero_conservando_ambos_movimientos(
    client, empresa, cuentas, registrar
):
    caja = cuentas["1105"]
    comprobante = registrar(
        [
            {"cuenta_id": caja.id, "debito": "500000.00", "credito": "0.00"},
            {"cuenta_id": cuentas["4135"].id, "debito": "0.00", "credito": "500000.00"},
        ],
    )
    client.post(f"/api/comprobantes/{comprobante['id']}/revertir")

    cuerpo = _consultar(client, empresa.id, caja.id).json()
    # La trazabilidad exige ver el asiento original y su reversión, no que desaparezcan.
    assert len(cuerpo["movimientos"]) == 2
    assert cuerpo["saldo_final"] == "0.00"
    assert cuerpo["total_debito"] == cuerpo["total_credito"] == "500000.00"


def test_saldo_inicial_acumula_lo_anterior_al_rango(client, empresa, cuentas, registrar):
    caja = cuentas["1105"]
    registrar(
        [
            {"cuenta_id": caja.id, "debito": "300000.00", "credito": "0.00"},
            {"cuenta_id": cuentas["4135"].id, "debito": "0.00", "credito": "300000.00"},
        ],
        fecha="2025-01-05",
    )
    registrar(
        [
            {"cuenta_id": caja.id, "debito": "100000.00", "credito": "0.00"},
            {"cuenta_id": cuentas["4135"].id, "debito": "0.00", "credito": "100000.00"},
        ],
        fecha="2025-01-25",
    )

    cuerpo = _consultar(client, empresa.id, caja.id, desde="2025-01-20", hasta="2025-01-31").json()
    assert cuerpo["saldo_inicial"] == "300000.00"
    assert len(cuerpo["movimientos"]) == 1
    # El acumulado arranca desde el saldo inicial, no desde cero.
    assert cuerpo["movimientos"][0]["saldo"] == "400000.00"


def test_movimiento_expone_tercero_y_referencia_del_comprobante(
    client, empresa, cuentas, tercero, registrar
):
    proveedores = cuentas["2205"]
    comprobante = registrar(
        [
            {"cuenta_id": cuentas["5105"].id, "debito": "100000.00", "credito": "0.00"},
            {
                "cuenta_id": proveedores.id,
                "debito": "0.00",
                "credito": "100000.00",
                "tercero_id": tercero.id,
                "descripcion": "Factura FV-001",
            },
        ],
    )

    movimiento = _consultar(client, empresa.id, proveedores.id).json()["movimientos"][0]
    assert movimiento["numero"] == comprobante["numero"]
    assert movimiento["tercero_nombre"] == tercero.nombre
    assert movimiento["descripcion"] == "Factura FV-001"


def test_rango_invertido_se_rechaza(client, empresa, cuentas):
    respuesta = _consultar(
        client, empresa.id, cuentas["1105"].id, desde="2025-01-31", hasta="2025-01-01"
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "RANGO_INVALIDO"


def test_cuenta_de_otra_empresa_no_es_consultable(client, db, empresa, cuentas):
    otra = client.post(
        "/api/empresas", json={"nit": "901555444", "dv": "3", "razon_social": "Otra S.A.S."}
    ).json()
    respuesta = _consultar(client, otra["id"], cuentas["1105"].id)
    assert respuesta.status_code == 404
