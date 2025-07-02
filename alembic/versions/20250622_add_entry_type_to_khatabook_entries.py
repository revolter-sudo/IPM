"""add_entry_type_to_khatabook_entries

Revision ID: 20250622_add_entry_type
Revises: 20250621_132726
Create Date: 2025-06-22 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250622_add_entry_type"
down_revision = "20250621_132726"
branch_labels = None
depends_on = None


def upgrade():
    """Add entry_type column to khatabook_entries table"""
    # Add the entry_type column with default value 'Debit'
    op.add_column(
        "khatabook_entries",
        sa.Column(
            "entry_type", sa.String(length=50), nullable=False, server_default="Debit"
        ),
    )


def downgrade():
    """Remove entry_type column from khatabook_entries table"""
    # Drop the entry_type column
    op.drop_column("khatabook_entries", "entry_type")
