"""remove server default value from self attendance table

Revision ID: 4ccc75f2adea
Revises: 96e4d3838a55
Create Date: 2025-07-09 17:39:38.729285

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ccc75f2adea'
down_revision: Union[str, None, Sequence[str]] = '96e4d3838a55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Remove any existing server_default on the status column
    op.alter_column(
        'self_attendance',
        'status',
        existing_type=sa.String(length=20),
        server_default=None,
        existing_nullable=False
    )


def downgrade():
    # Re-add the previous server_default of 'present'
    op.alter_column(
        'self_attendance',
        'status',
        existing_type=sa.String(length=20),
        server_default=sa.text("'present'"),
        existing_nullable=False
    )
