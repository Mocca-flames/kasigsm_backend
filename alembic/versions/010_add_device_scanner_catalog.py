"""Add device scanner catalog tables."""

from alembic import op
import sqlalchemy as sa
from sqlmodel import SQLModel
from app.models.device_catalog import (
    IssueCategory,
    Chipset,
    DeviceBrand,
    Tool,
    ToolCapability,
    DeviceCompatibility,
)


revision = "010_add_device_scanner_catalog"
down_revision = "009_add_discount_promo_code"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "issue_category",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("slug", name="uq_issue_category_slug"),
    )
    op.create_index("ix_issue_category_slug", "issue_category", ["slug"])

    op.create_table(
        "chipset",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("key", name="uq_chipset_key"),
    )
    op.create_index("ix_chipset_key", "chipset", ["key"])

    op.create_table(
        "device_brand",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("slug", name="uq_device_brand_slug"),
    )
    op.create_index("ix_device_brand_slug", "device_brand", ["slug"])

    op.create_table(
        "device_tool",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website_url", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("slug", name="uq_device_tool_slug"),
    )
    op.create_index("ix_device_tool_slug", "device_tool", ["slug"])

    op.create_table(
        "tool_capability",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tool_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_slug", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tool_id"], ["device_tool.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "tool_id", "issue_slug", name="uq_tool_issue"
        ),
    )
    op.create_index("ix_tool_capability_tool_id", "tool_capability", ["tool_id"])
    op.create_index("ix_tool_capability_issue_slug", "tool_capability", ["issue_slug"])

    op.create_table(
        "device_compatibility",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tool_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_slug", sa.String(), nullable=True),
        sa.Column("chipset_key", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tool_id"], ["device_tool.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "tool_id", "brand_slug", "chipset_key", name="uq_tool_brand_chipset"
        ),
    )
    op.create_index("ix_device_compatibility_tool_id", "device_compatibility", ["tool_id"])
    op.create_index(
        "ix_device_compatibility_brand_slug", "device_compatibility", ["brand_slug"]
    )
    op.create_index(
        "ix_device_compatibility_chipset_key", "device_compatibility", ["chipset_key"]
    )


def downgrade():
    op.drop_index("ix_device_compatibility_chipset_key", table_name="device_compatibility")
    op.drop_index("ix_device_compatibility_brand_slug", table_name="device_compatibility")
    op.drop_index("ix_device_compatibility_tool_id", table_name="device_compatibility")
    op.drop_table("device_compatibility")

    op.drop_index("ix_tool_capability_issue_slug", table_name="tool_capability")
    op.drop_index("ix_tool_capability_tool_id", table_name="tool_capability")
    op.drop_table("tool_capability")

    op.drop_index("ix_device_tool_slug", table_name="device_tool")
    op.drop_table("device_tool")

    op.drop_index("ix_device_brand_slug", table_name="device_brand")
    op.drop_table("device_brand")

    op.drop_index("ix_chipset_key", table_name="chipset")
    op.drop_table("chipset")

    op.drop_index("ix_issue_category_slug", table_name="issue_category")
    op.drop_table("issue_category")
