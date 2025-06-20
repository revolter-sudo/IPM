"""add_unique_constraint_project_item_map

Revision ID: add_unique_constraint_project_item_map
Revises: e384ec734894
Create Date: 2025-06-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = '3160faadbcc2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add unique constraint to project_item_map table to prevent duplicate mappings.
    First, remove any existing duplicates by keeping only the most recent entry
    for each (project_id, item_id) combination.
    """
    
    # Step 1: Remove duplicate entries, keeping only the most recent one (highest id)
    op.execute("""
        DELETE FROM project_item_map 
        WHERE id NOT IN (
            SELECT MAX(id) 
            FROM project_item_map 
            GROUP BY project_id, item_id
        )
    """)
    
    # Step 2: Add the unique constraint
    op.create_unique_constraint(
        'uq_project_item',
        'project_item_map',
        ['project_id', 'item_id']
    )


def downgrade() -> None:
    """Remove the unique constraint."""
    op.drop_constraint('uq_project_item', 'project_item_map', type_='unique')
