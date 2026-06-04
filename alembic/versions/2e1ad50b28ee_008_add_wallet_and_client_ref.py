"""008_add_wallet_and_client_ref

Revision ID: 2e1ad50b28ee
Revises: ccf87ab75765
Create Date: 2026-06-04 15:56:13.696007

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

revision: str = '2e1ad50b28ee'
down_revision: Union[str, None] = 'ccf87ab75765'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('wallet',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('balance', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('status', sa.Enum('ACTIVE', 'DISABLED', name='walletstatus'), nullable=False),
    sa.Column('client_ref', sa.String(length=6), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wallet_user_id'), 'wallet', ['user_id'], unique=True)
    op.create_index(op.f('ix_wallet_client_ref'), 'wallet', ['client_ref'], unique=True)
    op.create_table('wallettopup',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('wallet_id', sa.Uuid(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('reference', sa.String(), nullable=True),
    sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED', name='wallettopupstatus'), nullable=False),
    sa.Column('proof_note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['wallet_id'], ['wallet.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wallettopup_wallet_id'), 'wallettopup', ['wallet_id'], unique=False)
    op.create_table('wallettransaction',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('wallet_id', sa.Uuid(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('type', sa.Enum('TOPUP', 'DEBIT', 'ADMIN_CREDIT', 'REFUND', name='wallettransactiontype'), nullable=False),
    sa.Column('reference', sa.String(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['wallet_id'], ['wallet.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wallettransaction_wallet_id'), 'wallettransaction', ['wallet_id'], unique=False)
    op.add_column('user', sa.Column('client_ref', sa.String(length=6), nullable=True))
    op.create_index(op.f('ix_user_client_ref'), 'user', ['client_ref'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_client_ref'), table_name='user')
    op.drop_column('user', 'client_ref')
    op.drop_index(op.f('ix_wallettransaction_wallet_id'), table_name='wallettransaction')
    op.drop_table('wallettransaction')
    op.drop_index(op.f('ix_wallettopup_wallet_id'), table_name='wallettopup')
    op.drop_table('wallettopup')
    op.drop_index(op.f('ix_wallet_client_ref'), table_name='wallet')
    op.drop_index(op.f('ix_wallet_user_id'), table_name='wallet')
    op.drop_table('wallet')
    # ### end Alembic commands ###