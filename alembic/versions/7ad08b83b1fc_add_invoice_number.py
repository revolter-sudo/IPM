"""add invoice number

Revision ID: 7ad08b83b1fc
Revises: d58a49460880
Create Date: 2025-06-14 01:58:15.487106

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "7ad08b83b1fc"
down_revision = "d58a49460880"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.add_column(
            sa.Column("invoice_number", sa.String(length=100), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.drop_column("invoice_number")
