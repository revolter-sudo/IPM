"""is_approved_by_admin

Revision ID: 47d20a6965d0
Revises: 0088460af7ec
Create Date: 2025-03-13 01:29:00.166310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47d20a6965d0'
down_revision: Union[str, None] = '0088460af7ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('payment_files',
                  sa.Column('is_approval_upload', sa.Boolean(),
                            nullable=False, server_default='false')
                  )


def downgrade():
    op.drop_column('payment_files', 'is_approval_upload')