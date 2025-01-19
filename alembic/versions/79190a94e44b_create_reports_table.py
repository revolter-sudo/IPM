"""create reports table

Revision ID: 79190a94e44b
Revises: 2110f0d51de7
Create Date: 2025-01-19 23:17:24.523562

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects.postgresql import UUID
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79190a94e44b'
down_revision: Union[str, None] = '2110f0d51de7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), sa.Identity(always=False, start=1, increment=1), primary_key=True, nullable=False),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('report_type', sa.String(length=20), nullable=False),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('generated_by', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('generated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['generated_by'], ['users.uuid']),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False)
    )


def downgrade() -> None:
    op.drop_table('reports')
