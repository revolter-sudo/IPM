"""create item_groups table

Revision ID: 96ebbf697ff8
Revises: 20250622_add_entry_type
Create Date: 2025-06-23 11:07:44.142655

"""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "96ebbf697ff8"
down_revision = "20250622_add_entry_type"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "item_groups",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "uuid", UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4
        ),
        sa.Column("item_groups", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.uuid"),
            nullable=False,
        ),
        sa.Column(
            "is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )


def downgrade():
    op.drop_table("item_groups")
