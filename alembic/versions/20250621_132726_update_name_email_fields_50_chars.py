"""update name and email fields to 50 characters for users, person, and user_data tables

Revision ID: 20250621_132726
Revises: 3160faadbcc2, 3e0c5c489867
Create Date: 2025-06-21 13:27:26.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250621_132726'
down_revision = ('3160faadbcc2', '3e0c5c489867')
branch_labels = None
depends_on = None


def upgrade():
    """Update name and email fields to 50 characters for users, person, and user_data tables only"""
    
    # Update users table - reduce name from 255 to 50
    op.alter_column('users', 'name',
                   existing_type=sa.String(255),
                   type_=sa.String(50),
                   existing_nullable=False)
    
    # Update person table - reduce name from 500 to 50
    op.alter_column('person', 'name',
                   existing_type=sa.String(500),
                   type_=sa.String(50),
                   existing_nullable=False)
    
    # Update user_data table - increase name from 20 to 50
    op.alter_column('user_data', 'name',
                   existing_type=sa.String(20),
                   type_=sa.String(50),
                   existing_nullable=False)
    
    # Update user_data table - increase email from 20 to 50
    op.alter_column('user_data', 'email',
                   existing_type=sa.String(20),
                   type_=sa.String(50),
                   existing_nullable=False)


def downgrade():
    """Revert name and email fields to their original lengths for users, person, and user_data tables"""
    
    # Revert users table - increase name back to 255
    op.alter_column('users', 'name',
                   existing_type=sa.String(50),
                   type_=sa.String(255),
                   existing_nullable=False)
    
    # Revert person table - increase name back to 500
    op.alter_column('person', 'name',
                   existing_type=sa.String(50),
                   type_=sa.String(500),
                   existing_nullable=False)
    
    # Revert user_data table - decrease name back to 20
    op.alter_column('user_data', 'name',
                   existing_type=sa.String(50),
                   type_=sa.String(20),
                   existing_nullable=False)
    
    # Revert user_data table - decrease email back to 20
    op.alter_column('user_data', 'email',
                   existing_type=sa.String(50),
                   type_=sa.String(20),
                   existing_nullable=False)
