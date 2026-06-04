"""007_add_otp

Revision ID: ccf87ab75765
Revises: 006
Create Date: 2026-06-03 22:07:11.394919

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'ccf87ab75765'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'otp',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('code_hash', sa.String(), nullable=False),
        sa.Column('purpose', sa.String(), nullable=False, server_default='REGISTER'),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_otp_email', 'otp', ['email'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_otp_email', 'otp')
    op.drop_table('otp')