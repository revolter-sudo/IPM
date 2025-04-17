"""create project_user_map table

Revision ID: add_project_user_map_table
Revises: ede455653854
Create Date: 2025-04-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_project_user_map_table'
down_revision = 'ede455653854'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'project_user_map',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.uuid'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.uuid'), nullable=False),
        sa.UniqueConstraint('user_id', 'project_id', name='uq_user_project')
    )


def downgrade():
    op.drop_table('project_user_map')
