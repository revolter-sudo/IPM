"""Make punch times timezone-aware

Revision ID: 15648844290a
Revises: ce27f7dbb4e4
Create Date: 2025-07-23 12:18:11.965404

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15648844290a'
down_revision: Union[str, None, Sequence[str]] = 'ce27f7dbb4e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # For PostgreSQL: change columns to TIMESTAMP WITH TIME ZONE
    op.alter_column('self_attendance', 'punch_in_time',
                    type_=sa.TIMESTAMP(timezone=True),
                    existing_nullable=True)

    op.alter_column('self_attendance', 'punch_out_time',
                    type_=sa.TIMESTAMP(timezone=True),
                    existing_nullable=True)

    op.alter_column('self_attendance', 'created_at',
                    type_=sa.TIMESTAMP(timezone=True),
                    existing_nullable=False)


def downgrade():
    # Rollback to timezone-naive TIMESTAMP
    op.alter_column('self_attendance', 'punch_in_time',
                    type_=sa.TIMESTAMP(timezone=False),
                    existing_nullable=True)

    op.alter_column('self_attendance', 'punch_out_time',
                    type_=sa.TIMESTAMP(timezone=False),
                    existing_nullable=True)

    op.alter_column('self_attendance', 'created_at',
                    type_=sa.TIMESTAMP(timezone=False),
                    existing_nullable=False)
