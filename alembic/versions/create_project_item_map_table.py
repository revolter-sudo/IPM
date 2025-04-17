"""create project_item_map table

Revision ID: create_project_item_map_table
Revises: add_project_user_map_table
Create Date: 2025-04-06 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_project_item_map_table'
down_revision = 'add_project_user_map_table'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'project_item_map',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('items.uuid'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.uuid'), nullable=False),
        sa.UniqueConstraint('item_id', 'project_id', name='uq_item_project')
    )


def downgrade():
    op.drop_table('project_item_map')
