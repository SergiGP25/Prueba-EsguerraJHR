from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS
from app.db import Base


class UvtValor(Base):
    """Valor vigente de la UVT para un año gravable.

    `anio` es único: la sincronización hace UPSERT sobre esa clave, de modo que
    ejecutarla varias veces actualiza el valor en lugar de duplicar filas.
    """

    __tablename__ = "uvt_valores"

    id: Mapped[int] = mapped_column(primary_key=True)
    anio: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(MONEY_MAX_DIGITS, MONEY_DECIMAL_PLACES))
    fuente: Mapped[str] = mapped_column(String(120))
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UvtSincronizacion(Base):
    """Bitácora: una fila por ejecución de la sincronización, exitosa o no.

    Es la trazabilidad exigida: permite auditar cuándo se consultó la fuente externa,
    cuántos intentos hicieron falta y por qué falló si fue el caso.
    """

    __tablename__ = "uvt_sincronizaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    anio: Mapped[int] = mapped_column(Integer, index=True)
    exitosa: Mapped[bool] = mapped_column(Boolean)
    intentos: Mapped[int] = mapped_column(Integer)
    valor: Mapped[Decimal | None] = mapped_column(
        Numeric(MONEY_MAX_DIGITS, MONEY_DECIMAL_PLACES), nullable=True
    )
    fuente: Mapped[str] = mapped_column(String(120))
    detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
