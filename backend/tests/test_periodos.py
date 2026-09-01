"""Períodos contables: alta y cierre.

El cierre es irreversible (la reapertura no está implementada, por decisión), así que
la vista de administración depende de estos códigos para avisar y para reaccionar
cuando la pantalla está desactualizada.
"""

from __future__ import annotations


def test_crear_periodo(client, empresa):
    respuesta = client.post(f"/api/empresas/{empresa.id}/periodos", json={"anio": 2025, "mes": 3})
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert (cuerpo["anio"], cuerpo["mes"]) == (2025, 3)
    assert cuerpo["estado"] == "abierto"


def test_crear_periodo_existente_se_rechaza(client, empresa):
    # El seed de la fixture ya dejó 2025-01 abierto.
    respuesta = client.post(f"/api/empresas/{empresa.id}/periodos", json={"anio": 2025, "mes": 1})
    assert respuesta.status_code == 409


def test_cerrar_periodo_dos_veces_se_rechaza(client, empresa):
    periodos = client.get(f"/api/empresas/{empresa.id}/periodos").json()
    enero = next(p for p in periodos if (p["anio"], p["mes"]) == (2025, 1))

    primero = client.post(f"/api/periodos/{enero['id']}/cerrar")
    assert primero.status_code == 200
    assert primero.json()["estado"] == "cerrado"

    segundo = client.post(f"/api/periodos/{enero['id']}/cerrar")
    assert segundo.status_code == 409
    assert segundo.json()["code"] == "PERIODO_YA_CERRADO"


def test_cerrar_un_periodo_inexistente_es_404(client):
    assert client.post("/api/periodos/9999/cerrar").status_code == 404


def test_mes_fuera_de_rango_se_rechaza(client, empresa):
    assert client.post(f"/api/empresas/{empresa.id}/periodos", json={"anio": 2025, "mes": 13}).status_code == 422
