"""Add item_id to project_attendance

Revision ID: 103d85bfcabc
Revises: 4ccc75f2adea
Create Date: 2025-07-10 13:41:21.420507

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '103d85bfcabc'
down_revision: Union[str, None, Sequence[str]] = '4ccc75f2adea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('project_attendance', sa.Column(
        'item_id',
        sa.UUID(as_uuid=True),
        sa.ForeignKey('items.uuid'),
        nullable=False
    ))


def downgrade():
    op.drop_column('project_attendance', 'item_id')
