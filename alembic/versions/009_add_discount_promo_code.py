"""009_add_discount_promo_code

Revision ID: 009_add_discount_promo_code
Revises: 2e1ad50b28ee
Create Date: 2026-06-05 00:48:02.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '009_add_discount_promo_code'
down_revision: Union[str, None] = '2e1ad50b28ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('order', sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'))
    op.add_column('order', sa.Column('discount_code', sa.String(length=50), nullable=True))
    op.add_column('order', sa.Column('discount_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0'))

    op.create_table(
        'promocode',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('discount_type', sa.Enum('PERCENTAGE', 'FIXED_AMOUNT', name='discounttype'), nullable=False),
        sa.Column('discount_value', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('min_order_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('max_discount_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('max_uses_per_user', sa.Integer(), nullable=True),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('applicable_categories', sa.String(), nullable=True),
        sa.Column('applicable_items', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('current_uses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_promocode_code'), 'promocode', ['code'], unique=True)

    op.create_table(
        'promocodeusage',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('promo_code_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('order_id', sa.Uuid(), nullable=True),
        sa.Column('discount_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('order_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['order.id'], ),
        sa.ForeignKeyConstraint(['promo_code_id'], ['promocode.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_promocodeusage_promo_code_id'), 'promocodeusage', ['promo_code_id'], unique=False)
    op.create_index(op.f('ix_promocodeusage_user_id'), 'promocodeusage', ['user_id'], unique=False)
    op.create_index(op.f('ix_promocodeusage_order_id'), 'promocodeusage', ['order_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_promocodeusage_order_id'), table_name='promocodeusage')
    op.drop_index(op.f('ix_promocodeusage_user_id'), table_name='promocodeusage')
    op.drop_index(op.f('ix_promocodeusage_promo_code_id'), table_name='promocodeusage')
    op.drop_table('promocodeusage')
    op.drop_index(op.f('ix_promocode_is_active'), table_name='promocode')
    op.drop_index(op.f('ix_promocode_code'), table_name='promocode')
    op.drop_table('promocode')

    op.alter_column('order', 'total_amount', nullable=False)
    op.drop_column('order', 'discount_amount')
    op.drop_column('order', 'discount_code')
    op.drop_column('order', 'subtotal')
