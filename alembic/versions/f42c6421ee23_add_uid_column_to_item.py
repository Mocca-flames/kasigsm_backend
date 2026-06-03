"""add uid column to item

Revision ID: f42c6421ee23
Revises: 003
Create Date: 2026-06-01 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f42c6421ee23"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("item", sa.Column("uid", sa.String(), nullable=True))
    op.create_index(op.f("ix_item_uid"), "item", ["uid"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_item_uid"), table_name="item")
    op.drop_column("item", "uid")
