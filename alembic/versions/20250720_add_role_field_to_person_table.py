"""Add role field to person table

Revision ID: 20250720aab
Revises: c4f8e9d2a1b3
Create Date: 2025-07-20 21:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250720aab'
down_revision: Union[str, None] = 'c4f8e9d2a1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add optional role field to person table.
    
    This field will store the same role values as the User.role field
    to allow role-based queries across both Users and Persons.
    """
    # Add role column to person table
    # Using String(30) to match the User.role field length
    # Making it nullable since not all Persons need to have roles assigned
    op.add_column(
        'person',
        sa.Column('role', sa.String(length=30), nullable=True)
    )


def downgrade() -> None:
    """Remove role field from person table."""
    op.drop_column('person', 'role')
