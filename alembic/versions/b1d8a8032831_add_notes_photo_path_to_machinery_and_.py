"""add notes, photo_path to machinery and create machinery_photos

Revision ID: b1d8a8032831
Revises: 8112f2d6f2f6
Create Date: 2025-07-14 12:01:08.131571

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid


# revision identifiers, used by Alembic.
revision: str = 'b1d8a8032831'
down_revision: Union[str, None, Sequence[str]] = '8112f2d6f2f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add notes and photo_path columns to machinery
    op.add_column('machinery', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('machinery', sa.Column('photo_path', sa.String(length=255), nullable=True))

    # Create machinery_photos table
    op.create_table(
        'machinery_photos',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('uuid', sa.Uuid(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4),
        sa.Column('machinery_id', sa.Uuid(as_uuid=True), sa.ForeignKey('machinery.uuid'), nullable=False),
        sa.Column('photo_path', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False)
    )


def downgrade():
    # Drop machinery_photos table
    op.drop_table('machinery_photos')
    # Remove columns from machinery
    op.drop_column('machinery', 'notes')
    op.drop_column('machinery', 'photo_path')
