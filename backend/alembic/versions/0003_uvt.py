"""Valor de la UVT por año y bitácora de sincronizaciones con la fuente externa.

Revision ID: 0003_uvt
Revises: 0002_reversion
Create Date: 2026-08-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_uvt"
down_revision: Union[str, None] = "0002_reversion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "uvt_valores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("valor", sa.Numeric(18, 2), nullable=False),
        sa.Column("fuente", sa.String(120), nullable=False),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # Único por año: es la clave del UPSERT que hace idempotente la sincronización.
    op.create_index("ix_uvt_valores_anio", "uvt_valores", ["anio"], unique=True)

    op.create_table(
        "uvt_sincronizaciones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("exitosa", sa.Boolean(), nullable=False),
        sa.Column("intentos", sa.Integer(), nullable=False),
        sa.Column("valor", sa.Numeric(18, 2), nullable=True),
        sa.Column("fuente", sa.String(120), nullable=False),
        sa.Column("detalle", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_uvt_sincronizaciones_anio", "uvt_sincronizaciones", ["anio"])


def downgrade() -> None:
    op.drop_index("ix_uvt_sincronizaciones_anio", table_name="uvt_sincronizaciones")
    op.drop_table("uvt_sincronizaciones")
    op.drop_index("ix_uvt_valores_anio", table_name="uvt_valores")
    op.drop_table("uvt_valores")
