from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS
from app.db import Base
from app.models.enums import EstadoComprobante

MONEY = Numeric(MONEY_MAX_DIGITS, MONEY_DECIMAL_PLACES)


class Comprobante(Base):
    __tablename__ = "comprobantes"
    __table_args__ = (
        UniqueConstraint("empresa_id", "periodo_id", "numero", name="uq_comprobante_numero_periodo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodos.id"), index=True)
    numero: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fecha: Mapped[date] = mapped_column(Date)
    descripcion: Mapped[str] = mapped_column(Text)
    estado: Mapped[EstadoComprobante] = mapped_column(
        Enum(
            EstadoComprobante,
            name="estado_comprobante",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=EstadoComprobante.BORRADOR,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    empresa: Mapped["Empresa"] = relationship(back_populates="comprobantes")
    periodo: Mapped["Periodo"] = relationship(back_populates="comprobantes")
    lineas: Mapped[list["LineaContable"]] = relationship(
        back_populates="comprobante",
        cascade="all, delete-orphan",
        order_by="LineaContable.id",
    )


class LineaContable(Base):
    __tablename__ = "lineas_contables"

    id: Mapped[int] = mapped_column(primary_key=True)
    comprobante_id: Mapped[int] = mapped_column(ForeignKey("comprobantes.id", ondelete="CASCADE"), index=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id"), index=True)
    tercero_id: Mapped[Optional[int]] = mapped_column(ForeignKey("terceros.id"), nullable=True)
    debito: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0.00"))
    credito: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0.00"))
    descripcion: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    comprobante: Mapped["Comprobante"] = relationship(back_populates="lineas")
    cuenta: Mapped["Cuenta"] = relationship(back_populates="lineas")
    tercero: Mapped[Optional["Tercero"]] = relationship()
