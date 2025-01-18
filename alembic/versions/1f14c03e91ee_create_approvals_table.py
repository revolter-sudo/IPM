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
        sa.Column('id', sa.Integer(), sa.Identity(always=False, start=1, increment=1), primary_key=True, nullable=False),
        sa.Column('uuid', sa.UUID(as_uuid=True), default=uuid.uuid4, nullable=False, unique=True),
        sa.Column('supporting_document', sa.String(length=255), nullable=True),
        sa.Column('payment_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('approver_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.uuid']),
        sa.ForeignKeyConstraint(['approver_id'], ['users.uuid']),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False)
    )


def downgrade() -> None:
    op.drop_table('approvals')
