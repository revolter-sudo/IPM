"""Add DefaultConfig table

Revision ID: add_default_config_table
Revises: 80696ef06f54
Create Date: 2023-07-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


# revision identifiers, used by Alembic.
revision = 'add_default_config_table'
down_revision = '80696ef06f54'
branch_labels = None
depends_on = None


def upgrade():
    # Create the default_config table
    op.create_table(
        'default_config',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('uuid', UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column('item_id', UUID(as_uuid=True), sa.ForeignKey('items.uuid'), nullable=False),
        sa.Column('admin_amount', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false'),
    )


def downgrade():
    # Drop the default_config table
    op.drop_table('default_config')
