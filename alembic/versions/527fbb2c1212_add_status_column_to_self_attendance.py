"""Add status column to self_attendance

Revision ID: 527fbb2c1212
Revises: 586a71ec72b5
Create Date: 2025-07-09 14:18:27.560813

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '527fbb2c1212'
down_revision: Union[str, None, Sequence[str]] = '586a71ec72b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("self_attendance", sa.Column("status", sa.String(length=20), nullable=False, server_default="present"))

def downgrade() -> None:
    op.drop_column('self_attendance', 'status')
