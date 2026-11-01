"""add_idempotency_key_to_inventory_transactions

Revision ID: a1b2c3d4e5f6
Revises: 69edbff59a6a
Create Date: 2026-11-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "69edbff59a6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add idempotency_key column (nullable, max 64 chars)
    op.add_column(
        "inventory_transactions",
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
    )
    # Partial unique index: only enforce uniqueness when idempotency_key IS NOT NULL
    op.create_index(
        "uq_tx_user_idempotency_key",
        "inventory_transactions",
        ["user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_tx_user_idempotency_key", table_name="inventory_transactions")
    op.drop_column("inventory_transactions", "idempotency_key")

