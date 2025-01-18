"""Creating Reports table

Revision ID: 7c7e172eaf85
Revises: 1f14c03e91ee
Create Date: 2025-01-12 14:44:40.693030

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c7e172eaf85'
down_revision: Union[str, None] = '1f14c03e91ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), sa.Identity(always=False, start=1, increment=1), primary_key=True, nullable=False),
        sa.Column('uuid', sa.UUID(as_uuid=True), default=uuid.uuid4, nullable=False, unique=True),
        sa.Column('report_type', sa.String(length=20), nullable=False),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('generated_by', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('generated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['generated_by'], ['users.uuid']),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False)
    )


def downgrade() -> None:
    op.drop_table('reports')
