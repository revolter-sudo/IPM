"""merge heads

Revision ID: merge_heads
Revises: add_project_user_map_table, b36ded34d38b
Create Date: 2025-04-06 12:30:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'merge_heads'
down_revision = ('add_project_user_map_table', 'b36ded34d38b')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
