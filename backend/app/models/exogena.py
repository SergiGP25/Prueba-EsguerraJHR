from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS
from app.db import Base

if TYPE_CHECKING:  # Solo para tipado: en runtime SQLAlchemy resuelve por su registro.
    from app.models.empresa import Empresa

MONEY = Numeric(MONEY_MAX_DIGITS, MONEY_DECIMAL_PLACES)


class ExogenaGeneracion(Base):
    """Registro de cada archivo de exógena generado (regla 14 del enunciado).

    El XML se guarda en la misma fila: la re-descarga no depende de un sistema de
    archivos ni de un volumen compartido entre réplicas. Para volúmenes grandes lo
    correcto sería un almacenamiento de objetos (ver README).
    """

    __tablename__ = "exogena_generaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    anio_gravable: Mapped[int] = mapped_column(Integer, index=True)

    # Parámetros usados, conservados para poder auditar y reproducir la generación.
    umbral_uvt: Mapped[Decimal] = mapped_column(MONEY)
    valor_uvt: Mapped[Decimal] = mapped_column(MONEY)
    umbral_pesos: Mapped[Decimal] = mapped_column(MONEY)

    total_registros: Mapped[int] = mapped_column(Integer)
    total_valor_bruto: Mapped[Decimal] = mapped_column(MONEY)
    total_retencion: Mapped[Decimal] = mapped_column(MONEY)

    # Terceros excluidos y el motivo: trazabilidad de lo que no quedó en el archivo.
    exclusiones: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)

    nombre_archivo: Mapped[str] = mapped_column(String(120))
    xml: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    empresa: Mapped[Empresa] = relationship()
