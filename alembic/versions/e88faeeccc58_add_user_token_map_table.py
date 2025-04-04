"""Add user_token_map table

Revision ID: e88faeeccc58
Revises: f54be59bf384
Create Date: 2025-03-28 22:21:47.843447

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e88faeeccc58'
down_revision: Union[str, None] = 'f54be59bf384'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'user_token_map',
        sa.Column(
            'id',
            sa.Integer(),
            sa.Identity(always=False, start=1, increment=1),
            primary_key=True,
            nullable=False
        ),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.uuid', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('fcm_token', sa.String(500), nullable=False),
        sa.Column('device_id', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )


def downgrade():
    op.drop_table('user_token_map')
