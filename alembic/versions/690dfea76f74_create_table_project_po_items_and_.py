"""Create table project po items and update project po table as well

Revision ID: 690dfea76f74
Revises: 497d4438cd47
Create Date: 2025-06-14 01:21:53.338279

"""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "690dfea76f74"
down_revision = "497d4438cd47"
branch_labels = None
depends_on = None


def upgrade():
    # ✅ 1. Add new columns to project_pos
    op.add_column(
        "project_pos", sa.Column("client_name", sa.String(length=255), nullable=True)
    )
    op.add_column("project_pos", sa.Column("po_date", sa.Date(), nullable=True))

    # ✅ 2. Make po_number unique
    op.create_unique_constraint(
        "uq_project_pos_po_number", "project_pos", ["po_number"]
    )

    # ✅ 3. Create project_po_items table
    op.create_table(
        "project_po_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            unique=True,
            nullable=False,
            default=uuid.uuid4,
        ),
        sa.Column(
            "project_po_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_pos.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("basic_value", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade():
    # Downgrade operations reverse the upgrade
    op.drop_table("project_po_items")
    op.drop_constraint("uq_project_pos_po_number", "project_pos", type_="unique")
    op.drop_column("project_pos", "po_date")
    op.drop_column("project_pos", "client_name")
