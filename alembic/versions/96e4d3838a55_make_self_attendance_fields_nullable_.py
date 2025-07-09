"""Make self_attendance fields nullable for day off

Revision ID: 96e4d3838a55
Revises: 527fbb2c1212
Create Date: 2025-07-09 14:51:37.423921

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96e4d3838a55'
down_revision: Union[str, None, Sequence[str]] = '527fbb2c1212'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('self_attendance', 'attendance_date', nullable=True)
    op.alter_column('self_attendance', 'punch_in_time', nullable=True)
    op.alter_column('self_attendance', 'punch_in_latitude', nullable=True)
    op.alter_column('self_attendance', 'punch_in_longitude', nullable=True)


def downgrade() -> None:
    op.alter_column('self_attendance', 'attendance_date', nullable=False)
    op.alter_column('self_attendance', 'punch_in_time', nullable=False)
    op.alter_column('self_attendance', 'punch_in_latitude', nullable=False)
    op.alter_column('self_attendance', 'punch_in_longitude', nullable=False)
