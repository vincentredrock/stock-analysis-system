"""Add stock sync statuses

Revision ID: 9b3a1f2c4d5e
Revises: 66f470c99de0
Create Date: 2026-04-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9b3a1f2c4d5e"
down_revision: Union[str, None] = "66f470c99de0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stock_sync_statuses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("synced_from", sa.Date(), nullable=True),
        sa.Column("synced_to", sa.Date(), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("records_upserted", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_id"),
    )
    op.create_index(op.f("ix_stock_sync_statuses_id"), "stock_sync_statuses", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_stock_sync_statuses_id"), table_name="stock_sync_statuses")
    op.drop_table("stock_sync_statuses")
