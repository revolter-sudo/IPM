"""Create Projects table

Revision ID: 72e6ff861b79
Revises: f001cf77ae0e
Create Date: 2025-01-12 14:25:05.540732

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72e6ff861b79'
down_revision: Union[str, None] = 'f001cf77ae0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'projects',
        sa.Column(
            'id',
            sa.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4
        ),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('projects')
