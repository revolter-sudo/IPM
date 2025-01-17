"""Create Users table

Revision ID: f001cf77ae0e
Revises: 
Create Date: 2025-01-12 14:13:38.248765

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f001cf77ae0e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), sa.Identity(always=False, start=1, increment=1), primary_key=True, nullable=False),
        sa.Column('uuid', sa.UUID(as_uuid=True), default=uuid.uuid4, nullable=False, unique=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.BigInteger(), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=30), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True)
    )


def downgrade() -> None:
    op.drop_table('users')
