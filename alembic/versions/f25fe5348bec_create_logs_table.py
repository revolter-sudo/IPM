"""Create Logs table

Revision ID: f25fe5348bec
Revises: 7c7e172eaf85
Create Date: 2025-01-12 14:48:13.547098

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f25fe5348bec'
down_revision: Union[str, None] = '7c7e172eaf85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'logs',
        sa.Column(
            'id',
            sa.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4
        ),
        sa.Column(
            'entity',
            sa.String(length=255),
            nullable=False
        ),
        sa.Column(
            'action',
            sa.String(length=20),
            nullable=False
        ),
        sa.Column(
            'entity_id',
            sa.UUID(as_uuid=True),
            nullable=False
        ),
        sa.Column(
            'performed_by',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('users.id'),
            nullable=False
        ),
        sa.Column(
            'timestamp',
            sa.TIMESTAMP(),
            server_default=sa.func.now(),
            nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table('logs')
