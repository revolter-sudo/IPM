"""create inquiry_data table

Revision ID: 20250625_inquiry_data
Revises: 20250622_add_entry_type_to_khatabook_entries
Create Date: 2025-06-25 12:00:00.000000

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250625_inquiry_data'
down_revision: Union[str, None] = 'fa1ecc5cdb5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create inquiry_data table
    op.create_table(
        'inquiry_data',
        sa.Column('id', sa.Integer(), sa.Identity(always=False, start=1, increment=1), primary_key=True, nullable=False),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('phone_number', sa.String(length=15), nullable=False),
        sa.Column('project_type', sa.String(length=50), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False),
        sa.Column('city', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False)
    )
    
    # Create index for phone_number and project_type combination for uniqueness validation
    op.create_index('idx_inquiry_phone_project_type', 'inquiry_data', ['phone_number', 'project_type'])
    
    # Create index for created_at for performance
    op.create_index('idx_inquiry_created_at', 'inquiry_data', ['created_at'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_inquiry_created_at', 'inquiry_data')
    op.drop_index('idx_inquiry_phone_project_type', 'inquiry_data')
    
    # Drop table
    op.drop_table('inquiry_data')
