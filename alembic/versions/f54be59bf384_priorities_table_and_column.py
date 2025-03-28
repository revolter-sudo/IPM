"""priorities table and column

Revision ID: f54be59bf384
Revises: 3b4fb80bcff4
Create Date: 2025-03-26 22:34:27.075209

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f54be59bf384'
down_revision: Union[str, None] = '3b4fb80bcff4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1) Create 'priorities' table
    op.create_table(
        'priorities',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('priority', sa.String(length=50), nullable=False),
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default="false"),
    )

    # 2) Add 'priority_id' column to 'payments' table referencing 'priorities'
    op.add_column('payments',
                  sa.Column(
                      'priority_id',
                      UUID(as_uuid=True),
                      sa.ForeignKey('priorities.uuid'),
                      nullable=True
                  )
                  )


def downgrade():
    op.drop_column('payments', 'priority_id')
    op.drop_table('priorities')
