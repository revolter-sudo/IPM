"""user_data

Revision ID: 67f307bc5ddb
Revises: 124e3c693cc9
Create Date: 2025-06-10 01:13:10.006578

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67f307bc5ddb'
down_revision: Union[str, None] = '124e3c693cc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_data',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('name', sa.String(length=20), nullable=False),
        sa.Column('email', sa.String(length=20), nullable=False),
        sa.Column('phone_number', sa.String(), nullable=False),
        sa.Column('password', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False)
    )


def downgrade() -> None:
    op.drop_table('user_data')
