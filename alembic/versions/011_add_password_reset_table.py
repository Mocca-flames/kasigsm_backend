"""011_add_password_reset_table


Revision ID: 011_add_password_reset_table
Revises: 010_add_device_scanner_catalog
Create Date: 2026-06-05
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "011_add_password_reset_table"
down_revision: Union[str, None] = "010_add_device_scanner_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_password_reset_email", "password_reset", ["email"], unique=False)
    op.create_index("ix_password_reset_token", "password_reset", ["token"], unique=True)
    op.create_index("ix_password_reset_user_id", "password_reset", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_password_reset_user_id", table_name="password_reset")
    op.drop_index("ix_password_reset_token", table_name="password_reset")
    op.drop_index("ix_password_reset_email", table_name="password_reset")
    op.drop_table("password_reset")
