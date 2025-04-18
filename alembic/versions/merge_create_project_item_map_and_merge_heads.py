"""merge create_project_item_map_table and merge_heads

Revision ID: merge_proj_map_merge_heads
Revises: create_project_item_map_table, merge_heads
Create Date: 2025-04-06 13:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'merge_proj_map_merge_heads'
down_revision = ('create_project_item_map_table', 'merge_heads')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
