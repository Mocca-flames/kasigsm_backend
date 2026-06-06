"""013_add_item_indexes

Revision ID: 013_add_item_indexes
Revises: 012_add_pw_reset_at_to_user
Create Date: 2026-06-05

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel

revision: str = "013_add_item_indexes"
down_revision: Union[str, None] = "012_add_pw_reset_at_to_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_item_visibility_category", "item", ["is_visible", "is_archived", "item_type", "category"])
    op.create_index("ix_providerlisting_item", "providerlisting", ["item_id", "is_active"])
    op.create_index("ix_providerlisting_provider", "providerlisting", ["provider_id", "is_active"])


def downgrade() -> None:
    op.drop_index("ix_providerlisting_provider", table_name="providerlisting")
    op.drop_index("ix_providerlisting_item", table_name="providerlisting")
    op.drop_index("ix_item_visibility_category", table_name="item")
