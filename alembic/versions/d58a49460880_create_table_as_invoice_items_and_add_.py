"""create table as invoice items and add columns in invoices table

Revision ID: d58a49460880
Revises: 690dfea76f74
Create Date: 2025-06-14 01:44:14.695259

"""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "d58a49460880"
down_revision = "690dfea76f74"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add invoice_date column if it doesn't exist
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.add_column(
            sa.Column("invoice_date", sa.Date(), nullable=True)
        )  # ✅ ADD, not alter
        batch_op.drop_column("invoice_item")  # ✅ DROP this column

    # 2. Create invoice_items table
    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("basic_value", sa.Float(), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade():
    # 1. Re-add invoice_item
    with op.batch_alter_table("invoices") as batch_op:
        batch_op.add_column(
            sa.Column("invoice_item", sa.String(length=255), nullable=True)
        )
        batch_op.drop_column("invoice_date")

    # 2. Drop invoice_items
    op.drop_table("invoice_items")
