"""add machinery table

Revision ID: 8112f2d6f2f6
Revises: 103d85bfcabc
Create Date: 2025-07-11 11:08:58.063343

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid


# revision identifiers, used by Alembic.
revision: str = '8112f2d6f2f6'
down_revision: Union[str, None, Sequence[str]] = '103d85bfcabc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'machinery',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uuid', sa.UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4),
        sa.Column('project_id', sa.UUID(as_uuid=True), sa.ForeignKey('projects.uuid'), nullable=False),
        sa.Column('sub_contractor_id', sa.UUID(as_uuid=True), sa.ForeignKey('person.uuid'), nullable=False),
        sa.Column('item_id', sa.UUID(as_uuid=True), sa.ForeignKey('items.uuid'), nullable=False),
        sa.Column('start_time', sa.TIMESTAMP(), nullable=False),
        sa.Column('end_time', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_by', sa.UUID(as_uuid=True), sa.ForeignKey('users.uuid'), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
    )


def downgrade():
    op.drop_table('machinery')
