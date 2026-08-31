"""Reversión de comprobantes: estado `reversado` y enlace al comprobante original.

Revision ID: 0002_reversion
Revises: 0001_inicial
Create Date: 2026-08-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_reversion"
down_revision: Union[str, None] = "0001_inicial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL permite añadir valores a un enum dentro de una transacción siempre que
    # no se usen en DML en la misma migración (aquí solo se declara).
    op.execute("ALTER TYPE estado_comprobante ADD VALUE IF NOT EXISTS 'reversado'")

    op.add_column(
        "comprobantes",
        sa.Column("reversa_comprobante_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_comprobantes_reversa_comprobante_id",
        "comprobantes",
        "comprobantes",
        ["reversa_comprobante_id"],
        ["id"],
    )
    # Un original solo puede tener un espejo. Como PostgreSQL admite múltiples NULL en un
    # índice único, los comprobantes normales no se ven afectados.
    op.create_unique_constraint(
        "uq_comprobante_reversa_unica",
        "comprobantes",
        ["reversa_comprobante_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_comprobante_reversa_unica", "comprobantes", type_="unique")
    op.drop_constraint("fk_comprobantes_reversa_comprobante_id", "comprobantes", type_="foreignkey")
    op.drop_column("comprobantes", "reversa_comprobante_id")
    # El valor 'reversado' no se elimina del enum: PostgreSQL no soporta DROP VALUE.
    # Revertirlo exigiría recrear el tipo, lo que no aporta valor en un downgrade.
