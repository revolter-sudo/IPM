"""Add is_late to invoice payments

Revision ID: 497d4438cd47
Revises: 59c341bd7fb0
Create Date: 2025-06-13 10:50:50.536944

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '497d4438cd47'
down_revision = '59c341bd7fb0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('invoice_payments', sa.Column('is_late', sa.Boolean(), nullable=True))


def downgrade():
     op.drop_column('invoice_payments', 'is_late')
