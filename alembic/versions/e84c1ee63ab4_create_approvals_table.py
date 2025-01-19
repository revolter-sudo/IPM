"""create approvals table

Revision ID: e84c1ee63ab4
Revises: 4c22eb719b6f
Create Date: 2025-01-19 23:20:40.889124

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e84c1ee63ab4'
down_revision: Union[str, None] = '4c22eb719b6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'approvals',
        sa.Column('id', sa.Integer(), sa.Identity(always=False, start=1, increment=1), primary_key=True, nullable=False),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, unique=True),
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
    op.drop_table("approvals")
