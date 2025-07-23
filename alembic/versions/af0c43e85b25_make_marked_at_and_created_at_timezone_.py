"""Make marked_at and created_at timezone aware

Revision ID: af0c43e85b25
Revises: 15648844290a
Create Date: 2025-07-23 13:57:02.426966

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af0c43e85b25'
down_revision: Union[str, None, Sequence[str]] = '15648844290a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Upgrade to timezone-aware TIMESTAMP
    op.alter_column('project_attendance', 'marked_at',
                    type_=sa.TIMESTAMP(timezone=True),
                    existing_nullable=False,
                    existing_server_default=sa.text('now()'))

    op.alter_column('project_attendance', 'created_at',
                    type_=sa.TIMESTAMP(timezone=True),
                    existing_nullable=False,
                    existing_server_default=sa.text('now()'))


def downgrade():
    # Revert to timezone-naive TIMESTAMP
    op.alter_column('project_attendance', 'marked_at',
                    type_=sa.TIMESTAMP(timezone=False),
                    existing_nullable=False,
                    existing_server_default=sa.text('now()'))

    op.alter_column('project_attendance', 'created_at',
                    type_=sa.TIMESTAMP(timezone=False),
                    existing_nullable=False,
                    existing_server_default=sa.text('now()'))
