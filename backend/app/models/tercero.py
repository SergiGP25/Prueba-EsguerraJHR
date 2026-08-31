from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:  # Solo para tipado: en runtime SQLAlchemy resuelve por su registro.
    from app.models.empresa import Empresa


class Tercero(Base):
    """Persona o empresa contra la que se registra un movimiento (proveedor, cliente, etc.)."""

    __tablename__ = "terceros"
    __table_args__ = (UniqueConstraint("empresa_id", "tipo_doc", "num_doc", name="uq_tercero_doc"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    tipo_doc: Mapped[str] = mapped_column(String(10), default="NIT")
    num_doc: Mapped[str] = mapped_column(String(20))
    # Opcional: solo aplica a NIT y solo se valida cuando viene informado.
    dv: Mapped[str | None] = mapped_column(String(1), nullable=True)
    nombre: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    empresa: Mapped[Empresa] = relationship(back_populates="terceros")
