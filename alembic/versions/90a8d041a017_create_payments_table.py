"""Create Payments table

Revision ID: 90a8d041a017
Revises: 72e6ff861b79
Create Date: 2025-01-12 14:27:57.236046

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '90a8d041a017'
down_revision: Union[str, None] = '72e6ff861b79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'payments',
        sa.Column(
            'id',
            sa.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4
        ),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'project_id',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('projects.id'),
            nullable=False
        ),
        sa.Column(
            'created_by',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('users.id'),
            nullable=False
        ),
        sa.Column(
            'status',
            sa.String(length=20),
            nullable=False
        ),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.TIMESTAMP(),
            server_default=sa.func.now(),
            nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.TIMESTAMP(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table('payments')
