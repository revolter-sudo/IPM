"""profile pic

Revision ID: 37b02a0f4dbe
Revises: c8770a12264f
Create Date: 2025-03-20 23:57:57.944201

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37b02a0f4dbe'
down_revision: Union[str, None] = 'c8770a12264f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('users', sa.Column('photo_path', sa.String(length=255), nullable=True))

def downgrade():
    op.drop_column('users', 'photo_path')