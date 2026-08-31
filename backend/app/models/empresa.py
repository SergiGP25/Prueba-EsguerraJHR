from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nit: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    dv: Mapped[str] = mapped_column(String(1))
    razon_social: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    cuentas: Mapped[list["Cuenta"]] = relationship(back_populates="empresa")
    periodos: Mapped[list["Periodo"]] = relationship(back_populates="empresa")
    terceros: Mapped[list["Tercero"]] = relationship(back_populates="empresa")
    comprobantes: Mapped[list["Comprobante"]] = relationship(back_populates="empresa")
