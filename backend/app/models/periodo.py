from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import EstadoPeriodo


class Periodo(Base):
    __tablename__ = "periodos"
    __table_args__ = (
        UniqueConstraint("empresa_id", "anio", "mes", name="uq_periodo_empresa_anio_mes"),
        CheckConstraint("mes >= 1 AND mes <= 12", name="ck_periodo_mes"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    anio: Mapped[int] = mapped_column(Integer)
    mes: Mapped[int] = mapped_column(Integer)
    estado: Mapped[EstadoPeriodo] = mapped_column(
        Enum(EstadoPeriodo, name="estado_periodo", values_callable=lambda x: [e.value for e in x]),
        default=EstadoPeriodo.ABIERTO,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    empresa: Mapped["Empresa"] = relationship(back_populates="periodos")
    comprobantes: Mapped[list["Comprobante"]] = relationship(back_populates="periodo")
