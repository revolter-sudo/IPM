"""Add khatabook_payment_map table

Revision ID: ce27f7dbb4e4
Revises: 20250720aab
Create Date: 2025-07-22 12:47:25.938779

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = 'ce27f7dbb4e4'
down_revision: Union[str, None, Sequence[str]] = '20250720aab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'khatabook_payment_map',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4),
        sa.Column('khatabook_id', UUID(as_uuid=True), sa.ForeignKey('khatabook_entries.uuid', ondelete='RESTRICT'), nullable=False),
        sa.Column('payment_id', UUID(as_uuid=True), sa.ForeignKey('payments.uuid', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.uuid', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table('khatabook_payment_map')
