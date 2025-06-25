"""create company info table

Revision ID: fa1ecc5cdb5c
Revises: 1d379f97a17f
Create Date: 2025-06-25 15:36:37.877004

"""
from alembic import op
import sqlalchemy as sa
import uuid
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = 'fa1ecc5cdb5c'
down_revision = '1d379f97a17f'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'company_info',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('uuid', UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4),
        sa.Column('years_of_experience', sa.Integer, nullable=False, default=0),
        sa.Column('no_of_staff', sa.Integer, nullable=False, default=0),
        sa.Column('user_construction', sa.String(length=255), nullable=False, server_default='false'),
        sa.Column('successfull_installations', sa.String(length=255), nullable=False, server_default='0'),
        sa.Column('logo_photo_url', sa.Text, nullable=True)
    )


def downgrade():
    op.drop_table('company_info')
