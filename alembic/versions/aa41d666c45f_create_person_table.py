"""Create Person Table

Revision ID: aa41d666c45f
Revises: d4ec67bc1d7b
Create Date: 2025-01-21 15:30:15.001356

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa41d666c45f'
down_revision: Union[str, None] = 'd4ec67bc1d7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'person',
        sa.Column(
            'id',
            sa.Integer(),
            sa.Identity(always=False, start=1, increment=1),
            primary_key=True,
            nullable=False
        ),
        sa.Column(
            'uuid',
            UUID(as_uuid=True),
            nullable=False,
            unique=True
        ),
        sa.Column('name', sa.String(length=25), nullable=False),
        sa.Column('account_number', sa.String(length=17), nullable=False),
        sa.Column('ifsc_code', sa.String(length=11), nullable=False),
        sa.Column('phone_number', sa.String(length=10), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False)
    )


def downgrade() -> None:
    op.drop_table("person")
