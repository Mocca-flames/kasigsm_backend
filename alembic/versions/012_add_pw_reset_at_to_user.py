"""012_add_pw_reset_at_to_user

Revision ID: 012_add_pw_reset_at_to_user
Revises: 011_add_password_reset_table
Create Date: 2026-06-05
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "012_add_pw_reset_at_to_user"
down_revision: Union[str, None] = "011_add_password_reset_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "password_reset_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user", "password_reset_at")
