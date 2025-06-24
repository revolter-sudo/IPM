"""create salary table

Revision ID: 1d379f97a17f
Revises: d92f2734cb12
Create Date: 2025-06-24 11:02:06.378652

"""
from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision = '1d379f97a17f'
down_revision = 'd92f2734cb12'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'salary',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uuid', sa.UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4),
        sa.Column('user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.uuid'), nullable=False),
        sa.Column('project_id', sa.UUID(as_uuid=True), sa.ForeignKey('projects.uuid'), nullable=False),
        sa.Column('month', sa.String(length=20), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False, default=0.0),
        sa.Column('created_by', sa.UUID(as_uuid=True), sa.ForeignKey('users.uuid'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False)
    )


def downgrade():
    op.drop_table('salary')
