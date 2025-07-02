"""remove po_balnce & po_documents columns from projects

Revision ID: 59c341bd7fb0
Revises: 7e7bc80a70e2
Create Date: 2025-06-12 13:31:46.485194

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "59c341bd7fb0"
down_revision = "7e7bc80a70e2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("po_balance")
        batch_op.drop_column("po_document_path")


def downgrade():
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("po_balance", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("po_document_path", sa.Integer(), nullable=True))
