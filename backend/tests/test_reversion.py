"""Escenario 3 — reversión: corregir un comprobante contabilizado sin perder trazabilidad."""

from __future__ import annotations

import pytest


@pytest.fixture()
def contabilizado(client, empresa, cuentas, tercero):
    """Comprobante ya contabilizado sobre el que se ejercitan las reversiones."""
    borrador = client.post(
        f"/api/empresas/{empresa.id}/comprobantes",
        json={
            "fecha": "2025-01-15",
            "descripcion": "Compra con error",
            "lineas": [
                {"cuenta_id": cuentas["5105"].id, "debito": "1000000.00", "credito": "0.00"},
                {"cuenta_id": cuentas["2408"].id, "debito": "190000.00", "credito": "0.00"},
                {
                    "cuenta_id": cuentas["2205"].id,
                    "debito": "0.00",
                    "credito": "1190000.00",
                    "tercero_id": tercero.id,
                },
            ],
        },
    )
    return client.post(f"/api/comprobantes/{borrador.json()['id']}/contabilizar").json()


def test_reversion_crea_comprobante_espejo(client, contabilizado):
    respuesta = client.post(f"/api/comprobantes/{contabilizado['id']}/revertir")
    assert respuesta.status_code == 201, respuesta.text
    reversion = respuesta.json()

    assert reversion["estado"] == "contabilizado"
    assert reversion["reversa_comprobante_id"] == contabilizado["id"]
    assert reversion["numero"] == contabilizado["numero"] + 1
    # El espejo invierte débitos y créditos, por lo que los totales coinciden con el original.
    assert reversion["total_debito"] == contabilizado["total_credito"]
    assert reversion["total_credito"] == contabilizado["total_debito"]

    por_cuenta = {linea["cuenta_id"]: linea for linea in reversion["lineas"]}
    for original in contabilizado["lineas"]:
        espejo = por_cuenta[original["cuenta_id"]]
        assert espejo["debito"] == original["credito"]
        assert espejo["credito"] == original["debito"]
        assert espejo["tercero_id"] == original["tercero_id"]


def test_original_queda_marcado_y_conserva_sus_movimientos(client, contabilizado):
    client.post(f"/api/comprobantes/{contabilizado['id']}/revertir")

    original = client.get(f"/api/comprobantes/{contabilizado['id']}").json()
    assert original["estado"] == "reversado"
    # No se borra ni se edita: la trazabilidad exige que el asiento original siga existiendo.
    assert original["numero"] == contabilizado["numero"]
    assert original["total_debito"] == contabilizado["total_debito"]
    assert len(original["lineas"]) == len(contabilizado["lineas"])


def test_no_se_puede_reversar_dos_veces(client, contabilizado):
    assert client.post(f"/api/comprobantes/{contabilizado['id']}/revertir").status_code == 201

    respuesta = client.post(f"/api/comprobantes/{contabilizado['id']}/revertir")
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "COMPROBANTE_YA_REVERSADO"


def test_no_se_puede_reversar_un_borrador(client, empresa, cuentas):
    borrador = client.post(
        f"/api/empresas/{empresa.id}/comprobantes",
        json={
            "fecha": "2025-01-15",
            "descripcion": "Borrador",
            "lineas": [
                {"cuenta_id": cuentas["1105"].id, "debito": "1000.00", "credito": "0.00"},
                {"cuenta_id": cuentas["4135"].id, "debito": "0.00", "credito": "1000.00"},
            ],
        },
    )
    respuesta = client.post(f"/api/comprobantes/{borrador.json()['id']}/revertir")
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "REVERSION_ESTADO_INVALIDO"


def test_reversion_en_periodo_cerrado_se_rechaza(client, empresa, contabilizado):
    periodos = client.get(f"/api/empresas/{empresa.id}/periodos").json()
    enero = next(p for p in periodos if (p["anio"], p["mes"]) == (2025, 1))
    client.post(f"/api/periodos/{enero['id']}/cerrar")

    respuesta = client.post(f"/api/comprobantes/{contabilizado['id']}/revertir")
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "PERIODO_CERRADO"


def test_reversion_admite_fecha_en_otro_periodo_abierto(client, contabilizado, empresa):
    """Si enero se cerró, la corrección se registra en un período abierto (febrero)."""
    periodos = client.get(f"/api/empresas/{empresa.id}/periodos").json()
    enero = next(p for p in periodos if (p["anio"], p["mes"]) == (2025, 1))
    client.post(f"/api/periodos/{enero['id']}/cerrar")

    respuesta = client.post(
        f"/api/comprobantes/{contabilizado['id']}/revertir",
        json={"fecha": "2025-02-05", "descripcion": "Corrección registrada en febrero"},
    )
    assert respuesta.status_code == 201, respuesta.text
    reversion = respuesta.json()
    assert reversion["fecha"] == "2025-02-05"
    assert reversion["periodo_id"] != contabilizado["periodo_id"]
    # Numeración independiente por período: es el primero de febrero.
    assert reversion["numero"] == 1


def test_comprobante_reversado_no_se_puede_editar(client, contabilizado):
    client.post(f"/api/comprobantes/{contabilizado['id']}/revertir")

    respuesta = client.put(
        f"/api/comprobantes/{contabilizado['id']}",
        json={"descripcion": "Intento de alteración"},
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "COMPROBANTE_PROTEGIDO"
