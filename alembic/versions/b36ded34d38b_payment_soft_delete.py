"""payment soft delete

Revision ID: b36ded34d38b
Revises: 65c380462339
Create Date: 2025-04-05 23:26:06.001279

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b36ded34d38b'
down_revision: Union[str, None] = '65c380462339'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1) payment_files
    op.add_column(
        'payment_files',
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('FALSE'))
    )
    # Remove the default so future inserts don't keep overriding
    op.alter_column('payment_files', 'is_deleted', server_default=False)

    # 2) payment_items
    op.add_column(
        'payment_items',
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('FALSE'))
    )
    op.alter_column('payment_items', 'is_deleted', server_default=False)

    # 3) payment_status_history
    op.add_column(
        'payment_status_history',
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('FALSE'))
    )
    op.alter_column('payment_status_history', 'is_deleted', server_default=False)

    # 4) payment_edit_histories
    op.add_column(
        'payment_edit_histories',
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('FALSE'))
    )
    op.alter_column('payment_edit_histories', 'is_deleted', server_default=False)

    # Note: Payment already has is_deleted, so no changes needed there


def downgrade():
    # Reverse everything if you ever roll back:
    op.drop_column('payment_files', 'is_deleted')
    op.drop_column('payment_items', 'is_deleted')
    op.drop_column('payment_status_history', 'is_deleted')
    op.drop_column('payment_edit_histories', 'is_deleted')
