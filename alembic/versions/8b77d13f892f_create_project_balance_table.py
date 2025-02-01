"""create project balance table

Revision ID: 8b77d13f892f
Revises: 0ec6254abeca
Create Date: 2025-01-25 13:00:26.089938

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b77d13f892f'
down_revision: Union[str, None] = '0ec6254abeca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'project_balances',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("uuid", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('project_id', sa.UUID(as_uuid=True), sa.ForeignKey('projects.uuid'), nullable=False),
        sa.Column('adjustment', sa.Float, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
    )

    # Create an index on project_id for faster lookups
    op.create_index('idx_project_balances_project_id', 'project_balances', ['project_id'])


def downgrade():
    op.drop_index('idx_project_balances_project_id', table_name='project_balances')
    op.drop_table('project_balances')