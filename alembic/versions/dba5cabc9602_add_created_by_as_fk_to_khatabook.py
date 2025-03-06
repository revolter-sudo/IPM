"""Add created_by as FK to Khatabook

Revision ID: dba5cabc9602
Revises: f590bba3f9aa
Create Date: 2025-03-06 23:37:46.012660

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dba5cabc9602'
down_revision: Union[str, None] = 'f590bba3f9aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        'khatabook_entries',
        sa.Column(
            'created_by',
            UUID(as_uuid=True),
            sa.ForeignKey('users.uuid', ondelete="CASCADE"),
            nullable=False,
            server_default='7297fa98-342f-4fbe-b0b3-46dc6515cf35'
        ),
    )


def downgrade():
    op.drop_column('khatabook_entries', 'created_by')
