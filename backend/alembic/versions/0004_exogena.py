"""Información exógena: histórico de generaciones y DV opcional del tercero.

Revision ID: 0004_exogena
Revises: 0003_uvt
Create Date: 2026-08-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_exogena"
down_revision: Union[str, None] = "0003_uvt"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("terceros", sa.Column("dv", sa.String(1), nullable=True))

    op.create_table(
        "exogena_generaciones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("anio_gravable", sa.Integer(), nullable=False),
        sa.Column("umbral_uvt", sa.Numeric(18, 2), nullable=False),
        sa.Column("valor_uvt", sa.Numeric(18, 2), nullable=False),
        sa.Column("umbral_pesos", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_registros", sa.Integer(), nullable=False),
        sa.Column("total_valor_bruto", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_retencion", sa.Numeric(18, 2), nullable=False),
        sa.Column("exclusiones", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("nombre_archivo", sa.String(120), nullable=False),
        sa.Column("xml", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_exogena_generaciones_empresa_id", "exogena_generaciones", ["empresa_id"])
    op.create_index("ix_exogena_generaciones_anio_gravable", "exogena_generaciones", ["anio_gravable"])


def downgrade() -> None:
    op.drop_index("ix_exogena_generaciones_anio_gravable", table_name="exogena_generaciones")
    op.drop_index("ix_exogena_generaciones_empresa_id", table_name="exogena_generaciones")
    op.drop_table("exogena_generaciones")
    op.drop_column("terceros", "dv")
