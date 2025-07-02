"""Add is_deleted to khatabook_file and khatabook_item

Revision ID: ddac80339e4e
Revises: 20250625_inquiry_data
Create Date: 2025-07-02 11:44:31.705251

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ddac80339e4e'
down_revision = '20250625_inquiry_data'
branch_labels = None
depends_on = None

def upgrade():
    # Add is_deleted column to khatabook_files
    op.add_column('khatabook_files', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    # Add is_deleted column to khatabook_items
    op.add_column('khatabook_items', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade():
    # Drop is_deleted column from khatabook_files
    op.drop_column('khatabook_files', 'is_deleted')

    # Drop is_deleted column from khatabook_items
    op.drop_column('khatabook_items', 'is_deleted')