"""add technician table and status enum

Revision ID: 004
Revises: f42c6421ee23
Create Date: 2026-06-02

"""
from alembic import op
import sqlalchemy as sa


revision = "004"
down_revision = "f42c6421ee23"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE 'TECHNICIAN'")
    op.create_table(
        "technician",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", name="technicianstatus"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("specialization", sa.String(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_technician_user_id", "technician", ["user_id"], unique=True)
    with op.batch_alter_table("technician") as batch_op:
        batch_op.create_foreign_key("fk_technician_user_id", "user", ["user_id"], ["id"])
        batch_op.create_foreign_key("fk_technician_reviewed_by", "user", ["reviewed_by"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("technician") as batch_op:
        batch_op.drop_constraint("fk_technician_reviewed_by", type_="foreignkey")
        batch_op.drop_constraint("fk_technician_user_id", type_="foreignkey")
    op.drop_index("ix_technician_user_id", table_name="technician")
    op.drop_table("technician")
    op.execute("DROP TYPE technicianstatus")
