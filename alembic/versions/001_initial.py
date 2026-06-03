"""initial migration

Revision ID: 001
Revises:
Create Date: 2026-05-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "item",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("slug", sa.String(), unique=True, nullable=False, index=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "item_type",
            sa.Enum("SERVICE", "PRODUCT", name="itemtype"),
            nullable=False,
        ),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("thumbnail", sa.String(), nullable=True),
        sa.Column("price_markup", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ZAR"),
        sa.Column("delivery_time", sa.String(), nullable=True),
        sa.Column("stock", sa.Integer(), nullable=True),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "provider",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(), unique=True, nullable=False),
        sa.Column("base_url", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "user",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("CLIENT", "ADMIN", name="userrole"),
            nullable=False,
            server_default="CLIENT",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "order",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "PAID", "FULFILLED", "CANCELLED", "REFUNDED", name="orderstatus"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("payment_ref", sa.String(), nullable=True),
        sa.Column("payment_gateway", sa.String(), nullable=True),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ZAR"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "orderitem",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
    )

    op.create_table(
        "credential",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("order_item_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "providerlisting",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("cost_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_preferred", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    with op.batch_alter_table("order", schema=None) as batch_op:
        batch_op.create_foreign_key("fk_order_user_id", "user", ["user_id"], ["id"])

    with op.batch_alter_table("orderitem", schema=None) as batch_op:
        batch_op.create_foreign_key("fk_orderitem_order_id", "order", ["order_id"], ["id"])
        batch_op.create_foreign_key("fk_orderitem_item_id", "item", ["item_id"], ["id"])

    with op.batch_alter_table("credential", schema=None) as batch_op:
        batch_op.create_foreign_key("fk_credential_item_id", "item", ["item_id"], ["id"])
        batch_op.create_foreign_key("fk_credential_order_item_id", "orderitem", ["order_item_id"], ["id"])

    with op.batch_alter_table("providerlisting", schema=None) as batch_op:
        batch_op.create_foreign_key("fk_providerlisting_item_id", "item", ["item_id"], ["id"])
        batch_op.create_foreign_key("fk_providerlisting_provider_id", "provider", ["provider_id"], ["id"])


def downgrade() -> None:
    op.drop_table("providerlisting")
    op.drop_table("credential")
    op.drop_table("orderitem")
    op.drop_table("order")
    op.drop_table("user")
    op.drop_table("provider")
    op.drop_table("item")

    op.execute("DROP TYPE IF EXISTS itemtype")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS orderstatus")