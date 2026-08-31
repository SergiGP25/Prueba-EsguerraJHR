"""Revisión inicial: dominio contable.

Revision ID: 0001_inicial
Revises:
Create Date: 2026-08-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_inicial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    naturaleza = sa.Enum("debito", "credito", name="naturaleza_cuenta")
    estado_periodo = sa.Enum("abierto", "cerrado", name="estado_periodo")
    estado_comprobante = sa.Enum("borrador", "contabilizado", name="estado_comprobante")

    op.create_table(
        "empresas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nit", sa.String(20), nullable=False),
        sa.Column("dv", sa.String(1), nullable=False),
        sa.Column("razon_social", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_empresas_nit", "empresas", ["nit"], unique=True)

    op.create_table(
        "cuentas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("naturaleza", naturaleza, nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("empresa_id", "codigo", name="uq_cuenta_empresa_codigo"),
    )
    op.create_index("ix_cuentas_empresa_id", "cuentas", ["empresa_id"])

    op.create_table(
        "periodos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("mes", sa.Integer(), nullable=False),
        sa.Column("estado", estado_periodo, nullable=False, server_default="abierto"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("empresa_id", "anio", "mes", name="uq_periodo_empresa_anio_mes"),
        sa.CheckConstraint("mes >= 1 AND mes <= 12", name="ck_periodo_mes"),
    )
    op.create_index("ix_periodos_empresa_id", "periodos", ["empresa_id"])

    op.create_table(
        "terceros",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("tipo_doc", sa.String(10), nullable=False, server_default="NIT"),
        sa.Column("num_doc", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("empresa_id", "tipo_doc", "num_doc", name="uq_tercero_doc"),
    )
    op.create_index("ix_terceros_empresa_id", "terceros", ["empresa_id"])

    op.create_table(
        "comprobantes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("periodo_id", sa.Integer(), sa.ForeignKey("periodos.id"), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=True),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("estado", estado_comprobante, nullable=False, server_default="borrador"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("empresa_id", "periodo_id", "numero", name="uq_comprobante_numero_periodo"),
    )
    op.create_index("ix_comprobantes_empresa_id", "comprobantes", ["empresa_id"])
    op.create_index("ix_comprobantes_periodo_id", "comprobantes", ["periodo_id"])

    op.create_table(
        "lineas_contables",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("comprobante_id", sa.Integer(), sa.ForeignKey("comprobantes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cuenta_id", sa.Integer(), sa.ForeignKey("cuentas.id"), nullable=False),
        sa.Column("tercero_id", sa.Integer(), sa.ForeignKey("terceros.id"), nullable=True),
        sa.Column("debito", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("credito", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("descripcion", sa.String(255), nullable=True),
    )
    op.create_index("ix_lineas_contables_comprobante_id", "lineas_contables", ["comprobante_id"])
    op.create_index("ix_lineas_contables_cuenta_id", "lineas_contables", ["cuenta_id"])


def downgrade() -> None:
    op.drop_table("lineas_contables")
    op.drop_table("comprobantes")
    op.drop_table("terceros")
    op.drop_table("periodos")
    op.drop_table("cuentas")
    op.drop_table("empresas")
    sa.Enum(name="naturaleza_cuenta").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="estado_periodo").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="estado_comprobante").drop(op.get_bind(), checkfirst=True)
