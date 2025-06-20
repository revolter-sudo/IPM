"""Add Project User Item Map Table

Revision ID: 0e43e71d3686
Revises: 1849b56b0213
Create Date: 2025-06-05 16:01:55.881380

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision: str = '0e43e71d3686'
down_revision: Union[str, None] = '1849b56b0213'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'project_user_item_map',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('uuid', sa.Uuid(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4),
        sa.Column('project_id', sa.Uuid(as_uuid=True), sa.ForeignKey('projects.uuid'), nullable=False),
        sa.Column('user_id', sa.Uuid(as_uuid=True), sa.ForeignKey('users.uuid'), nullable=False),
        sa.Column('item_id', sa.Uuid(as_uuid=True), sa.ForeignKey('items.uuid'), nullable=False),
    )



def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('project_user_item_map')
    
