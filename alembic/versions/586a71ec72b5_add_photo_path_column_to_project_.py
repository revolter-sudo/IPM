"""Add photo_path column to project_attendance

Revision ID: 586a71ec72b5
Revises: 20250628_attendance_indexes
Create Date: 2025-07-09 11:38:07.708593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '586a71ec72b5'
down_revision: Union[str, None, Sequence[str]] = '20250628_attendance_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('project_attendance', sa.Column('photo_path', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('project_attendance', 'photo_path')