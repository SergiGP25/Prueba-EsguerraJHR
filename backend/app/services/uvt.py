"""Integración con la fuente externa del valor de la UVT.

Decisiones (ver README):

- **Proveedor detrás de un protocolo.** El servicio depende de `ProveedorUvt`, no de
  un cliente HTTP concreto: cambiar el simulado por uno real (httpx contra la DIAN)
  no toca la lógica de sincronización ni las pruebas.
- **Sin bloquear la petición HTTP.** El endpoint encola la sincronización con
  `BackgroundTasks` y responde 202; la tarea abre su propia sesión de base de datos.
- **Idempotencia.** El valor se guarda con UPSERT sobre `anio`, así que repetir la
  ejecución actualiza en lugar de duplicar.
- **Trazabilidad.** Cada ejecución deja una fila en `uvt_sincronizaciones`, tanto si
  termina bien como si agota los reintentos.
"""

from __future__ import annotations

import logging
import time
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.core.money import parse_money
from app.db import SessionLocal
from app.models import UvtSincronizacion, UvtValor

logger = logging.getLogger(__name__)

# Valores oficiales publicados por la DIAN. Sirven de respaldo del proveedor simulado.
UVT_POR_ANIO: dict[int, str] = {
    2021: "36308.00",
    2022: "38004.00",
    2023: "42412.00",
    2024: "47065.00",
    2025: "49799.00",
    2026: "52374.00",
}


class FuenteUvtNoDisponible(RuntimeError):
    """Fallo transitorio de la fuente externa: justifica reintentar."""


class ProveedorUvt(Protocol):
    """Contrato mínimo que debe cumplir cualquier fuente de UVT."""

    nombre: str

    def obtener(self, anio: int) -> Decimal: ...


class ProveedorUvtSimulado:
    """Proveedor de pruebas que imita una integración real.

    `fallar_veces` simula fallos transitorios de red para ejercitar los reintentos
    sin depender de que la fuente real esté caída.
    """

    nombre = "simulado:dian"

    def __init__(self, fallar_veces: int = 0, latencia_segundos: float = 0.0) -> None:
        self._fallos_restantes = fallar_veces
        self._latencia = latencia_segundos

    def obtener(self, anio: int) -> Decimal:
        if self._latencia:
            time.sleep(self._latencia)
        if self._fallos_restantes > 0:
            self._fallos_restantes -= 1
            raise FuenteUvtNoDisponible("La fuente externa no respondió (fallo simulado).")
        if anio not in UVT_POR_ANIO:
            raise FuenteUvtNoDisponible(f"La fuente no publica un valor de UVT para {anio}.")
        return parse_money(UVT_POR_ANIO[anio])


def _guardar_valor(db: Session, anio: int, valor: Decimal, fuente: str) -> None:
    """UPSERT sobre `anio`: repetir la sincronización no genera duplicados."""
    db.execute(
        insert(UvtValor)
        .values(anio=anio, valor=valor, fuente=fuente)
        .on_conflict_do_update(
            index_elements=[UvtValor.anio],
            set_={"valor": valor, "fuente": fuente},
        )
    )


def sincronizar(
    db: Session,
    anio: int,
    proveedor: ProveedorUvt | None = None,
    max_intentos: int = 3,
    espera_segundos: float = 0.5,
) -> UvtSincronizacion:
    """Consulta la fuente externa con reintentos y registra el resultado."""
    fuente = proveedor or ProveedorUvtSimulado()
    ultimo_error: str | None = None

    for intento in range(1, max_intentos + 1):
        try:
            valor = fuente.obtener(anio)
        except FuenteUvtNoDisponible as exc:
            ultimo_error = str(exc)
            logger.warning("UVT %s: intento %s/%s falló: %s", anio, intento, max_intentos, exc)
            if intento < max_intentos:
                time.sleep(espera_segundos * intento)  # backoff lineal, suficiente a esta escala
            continue

        _guardar_valor(db, anio, valor, fuente.nombre)
        registro = UvtSincronizacion(
            anio=anio,
            exitosa=True,
            intentos=intento,
            valor=valor,
            fuente=fuente.nombre,
        )
        db.add(registro)
        db.flush()
        logger.info("UVT %s sincronizada en %s intento(s): %s", anio, intento, valor)
        return registro

    registro = UvtSincronizacion(
        anio=anio,
        exitosa=False,
        intentos=max_intentos,
        valor=None,
        fuente=fuente.nombre,
        detalle=ultimo_error,
    )
    db.add(registro)
    db.flush()
    logger.error("UVT %s: se agotaron %s intentos. Último error: %s", anio, max_intentos, ultimo_error)
    return registro


def sincronizar_en_segundo_plano(anio: int) -> None:
    """Punto de entrada de `BackgroundTasks`: abre su propia sesión y confirma.

    No puede reutilizar la sesión de la petición porque esta ya se cerró al responder.
    """
    db = SessionLocal()
    try:
        sincronizar(db, anio)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Falló la sincronización de UVT en segundo plano para %s", anio)
    finally:
        db.close()


def valor_uvt(db: Session, anio: int) -> Decimal:
    """Valor almacenado para el año, o error de dominio si aún no se ha sincronizado."""
    valor = db.scalar(select(UvtValor.valor).where(UvtValor.anio == anio))
    if valor is None:
        raise DomainError(
            "UVT_NO_DISPONIBLE",
            f"No hay valor de UVT registrado para {anio}. "
            f"Ejecute POST /api/uvt/sincronizar?anio={anio} antes de generar el reporte.",
        )
    return valor


def listar_valores(db: Session) -> list[UvtValor]:
    return list(db.scalars(select(UvtValor).order_by(UvtValor.anio.desc())).all())


def listar_sincronizaciones(db: Session, limite: int = 50) -> list[UvtSincronizacion]:
    return list(
        db.scalars(
            select(UvtSincronizacion).order_by(UvtSincronizacion.id.desc()).limit(limite)
        ).all()
    )
