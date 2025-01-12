"""Create Approvals table

Revision ID: 1f14c03e91ee
Revises: 90a8d041a017
Create Date: 2025-01-12 14:33:56.195974

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f14c03e91ee'
down_revision: Union[str, None] = '90a8d041a017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'approvals',
        sa.Column(
            'id', sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
        ),
        sa.Column('supporting_document', sa.String(length=255), nullable=True),
        sa.Column(
            'payment_id',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('payments.id'),
            nullable=False
        ),
        sa.Column(
            'approver_id',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('users.id'),
            nullable=False
        ),
        sa.Column(
            'status',
            sa.String(length=20),
            nullable=False),
        sa.Column('remarks', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('approvals')
