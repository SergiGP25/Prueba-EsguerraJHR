from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import NaturalezaCuenta


class Cuenta(Base):
    """Plan de cuentas plano por empresa.

    Decisión de diseño (Día 1): sin jerarquía. El código (p. ej. 1105, 5105)
    es suficiente para identificar la cuenta. Una jerarquía PUCx se puede
    añadir después con cuenta_padre_id sin romper movimientos ya contabilizados.
    """

    __tablename__ = "cuentas"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo", name="uq_cuenta_empresa_codigo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    codigo: Mapped[str] = mapped_column(String(20))
    nombre: Mapped[str] = mapped_column(String(255))
    naturaleza: Mapped[NaturalezaCuenta] = mapped_column(
        Enum(NaturalezaCuenta, name="naturaleza_cuenta", values_callable=lambda x: [e.value for e in x])
    )
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    empresa: Mapped["Empresa"] = relationship(back_populates="cuentas")
    lineas: Mapped[list["LineaContable"]] = relationship(back_populates="cuenta")
