"""Integración con la fuente externa de la UVT: reintentos, idempotencia y trazabilidad."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.core.exceptions import DomainError
from app.models import UvtSincronizacion, UvtValor
from app.services import uvt


def test_sincronizacion_exitosa_guarda_valor_y_bitacora(db):
    registro = uvt.sincronizar(db, 2025, proveedor=uvt.ProveedorUvtSimulado())

    assert registro.exitosa is True
    assert registro.intentos == 1
    assert uvt.valor_uvt(db, 2025) == registro.valor
    assert format(registro.valor, "f") == "49799.00"


def test_reintenta_ante_fallos_transitorios(db):
    proveedor = uvt.ProveedorUvtSimulado(fallar_veces=2)

    registro = uvt.sincronizar(db, 2025, proveedor=proveedor, espera_segundos=0)

    assert registro.exitosa is True
    # Dos fallos y un acierto: la traza deja constancia del esfuerzo.
    assert registro.intentos == 3


def test_reintentos_agotados_registran_el_fallo_sin_guardar_valor(db):
    proveedor = uvt.ProveedorUvtSimulado(fallar_veces=99)

    registro = uvt.sincronizar(db, 2025, proveedor=proveedor, max_intentos=3, espera_segundos=0)

    assert registro.exitosa is False
    assert registro.intentos == 3
    assert registro.detalle is not None
    assert db.scalar(select(UvtValor).where(UvtValor.anio == 2025)) is None


def test_ejecuciones_repetidas_no_duplican_el_valor(db):
    for _ in range(3):
        uvt.sincronizar(db, 2025, proveedor=uvt.ProveedorUvtSimulado())

    filas = db.scalar(select(func.count()).select_from(UvtValor).where(UvtValor.anio == 2025))
    assert filas == 1
    # Pero cada ejecución sí deja su propia traza de auditoría.
    ejecuciones = db.scalar(
        select(func.count()).select_from(UvtSincronizacion).where(UvtSincronizacion.anio == 2025)
    )
    assert ejecuciones == 3


def test_anio_sin_publicar_falla_de_forma_controlada(db):
    registro = uvt.sincronizar(
        db, 1999, proveedor=uvt.ProveedorUvtSimulado(), max_intentos=1, espera_segundos=0
    )
    assert registro.exitosa is False
    assert "1999" in registro.detalle


def test_valor_uvt_faltante_es_un_error_de_dominio_accionable(db):
    with pytest.raises(DomainError) as error:
        uvt.valor_uvt(db, 2024)

    assert error.value.code == "UVT_NO_DISPONIBLE"
    assert "sincronizar" in error.value.message


def test_endpoint_de_sincronizacion_no_bloquea_la_peticion(client):
    respuesta = client.post("/api/uvt/sincronizar", params={"anio": 2025})

    # 202: la petición se acepta y la consulta externa ocurre fuera del ciclo HTTP.
    assert respuesta.status_code == 202
    assert respuesta.json()["estado"] == "encolada"


def test_endpoints_de_consulta_exponen_valores_y_bitacora(client, db):
    uvt.sincronizar(db, 2025, proveedor=uvt.ProveedorUvtSimulado())

    valores = client.get("/api/uvt").json()
    assert valores[0]["anio"] == 2025
    assert valores[0]["valor"] == "49799.00"

    historial = client.get("/api/uvt/sincronizaciones").json()
    assert historial[0]["exitosa"] is True
    assert historial[0]["fuente"] == "simulado:dian"
