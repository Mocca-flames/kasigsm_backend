"""add_category_and_provider_category_markup

Revision ID: 005
Revises: 004
Create Date: 2026-06-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "category",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(), unique=True, nullable=False, index=True),
        sa.Column("slug", sa.String(), unique=True, nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "providercategorymarkup",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("category", sa.String(), nullable=False, index=True),
        sa.Column("price_markup", sa.Numeric(12, 2), nullable=False),
    )

    op.create_index("uq_provider_category", "providercategorymarkup", ["provider_id", "category"], unique=True)

    op.execute(
        """
        INSERT INTO category (id, name, slug, description, is_active, created_at)
        SELECT gen_random_uuid(), category, lower(regexp_replace(category, '[^a-z0-9-]+', '-', 'g')), NULL, true, now()
        FROM (SELECT DISTINCT category FROM item WHERE category IS NOT NULL) sub
        """
    )


def downgrade() -> None:
    op.drop_index("uq_provider_category", table_name="providercategorymarkup")
    op.drop_table("providercategorymarkup")
    op.drop_table("category")
