"""multiple POs and invoices

Revision ID: 7e7bc80a70e2
Revises: 0e43e71d3686
Create Date: 2025-06-11 19:55:44.941357

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7e7bc80a70e2"
down_revision: Union[str, None] = "0e43e71d3686"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    existing_columns = {col["name"] for col in inspector.get_columns("invoices")}

    # 1. Create project_pos table if it doesn't exist
    if "project_pos" not in existing_tables:
        op.create_table(
            "project_pos",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column(
                "uuid",
                UUID(),
                nullable=False,
                unique=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "project_id", UUID(), sa.ForeignKey("projects.uuid"), nullable=False
            ),
            sa.Column("po_number", sa.String(100), nullable=True),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("file_path", sa.String(255), nullable=True),
            sa.Column(
                "created_by", UUID(), sa.ForeignKey("users.uuid"), nullable=False
            ),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "is_deleted", sa.Boolean(), nullable=False, server_default="false"
            ),
        )
        op.create_index("idx_project_pos_project_id", "project_pos", ["project_id"])
        op.create_index("idx_project_pos_created_by", "project_pos", ["created_by"])

    # 2. Add new columns to invoices table if missing
    if "project_po_id" not in existing_columns:
        op.add_column(
            "invoices",
            sa.Column(
                "project_po_id",
                UUID(),
                sa.ForeignKey("project_pos.uuid"),
                nullable=True,
            ),
        )
        op.create_index("idx_invoices_project_po_id", "invoices", ["project_po_id"])
    if "payment_status" not in existing_columns:
        op.add_column(
            "invoices",
            sa.Column(
                "payment_status",
                sa.String(20),
                nullable=False,
                server_default="not_paid",
            ),
        )
    if "total_paid_amount" not in existing_columns:
        op.add_column(
            "invoices",
            sa.Column(
                "total_paid_amount", sa.Float(), nullable=False, server_default="0.0"
            ),
        )

    # 3. Create invoice_payments table if it doesn't exist
    if "invoice_payments" not in existing_tables:
        op.create_table(
            "invoice_payments",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column(
                "uuid",
                UUID(),
                nullable=False,
                unique=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "invoice_id", UUID(), sa.ForeignKey("invoices.uuid"), nullable=False
            ),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("payment_date", sa.Date(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("payment_method", sa.String(50), nullable=True),
            sa.Column("reference_number", sa.String(100), nullable=True),
            sa.Column(
                "created_by", UUID(), sa.ForeignKey("users.uuid"), nullable=False
            ),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "is_deleted", sa.Boolean(), nullable=False, server_default="false"
            ),
        )
        op.create_index(
            "idx_invoice_payments_invoice_id", "invoice_payments", ["invoice_id"]
        )
        op.create_index(
            "idx_invoice_payments_created_by", "invoice_payments", ["created_by"]
        )
        op.create_index(
            "idx_invoice_payments_payment_date", "invoice_payments", ["payment_date"]
        )

    # 4. Remove server defaults from invoices
    try:
        op.alter_column("invoices", "payment_status", server_default=None)
        op.alter_column("invoices", "total_paid_amount", server_default=None)
    except Exception:
        pass


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    existing_columns = {col["name"] for col in inspector.get_columns("invoices")}

    # 1. Drop invoice_payments if exists
    if "invoice_payments" in existing_tables:
        op.drop_index(
            "idx_invoice_payments_payment_date", table_name="invoice_payments"
        )
        op.drop_index("idx_invoice_payments_created_by", table_name="invoice_payments")
        op.drop_index("idx_invoice_payments_invoice_id", table_name="invoice_payments")
        op.drop_table("invoice_payments")

    # 2. Remove new columns from invoices table if present
    if "project_po_id" in existing_columns:
        op.drop_index("idx_invoices_project_po_id", table_name="invoices")
        op.drop_column("invoices", "project_po_id")
    if "payment_status" in existing_columns:
        op.drop_column("invoices", "payment_status")
    if "total_paid_amount" in existing_columns:
        op.drop_column("invoices", "total_paid_amount")

    # 3. Drop project_pos table if exists
    if "project_pos" in existing_tables:
        op.drop_index("idx_project_pos_created_by", table_name="project_pos")
        op.drop_index("idx_project_pos_project_id", table_name="project_pos")
        op.drop_table("project_pos")
