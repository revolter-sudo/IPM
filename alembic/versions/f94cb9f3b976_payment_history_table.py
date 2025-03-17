"""payment history table

Revision ID: f94cb9f3b976
Revises: b4d087e09e89
Create Date: 2025-03-11 00:59:51.198948

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f94cb9f3b976'
down_revision: Union[str, None] = 'b4d087e09e89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'payment_edit_histories',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('payment_id', UUID(as_uuid=True), sa.ForeignKey('payments.uuid', ondelete='CASCADE'), nullable=False),
        sa.Column('old_amount', sa.Float(), nullable=False),
        sa.Column('new_amount', sa.Float(), nullable=False),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_by', UUID(as_uuid=True), sa.ForeignKey('users.uuid'), nullable=False),
    )


def downgrade():
    op.drop_table('payment_edit_histories')
