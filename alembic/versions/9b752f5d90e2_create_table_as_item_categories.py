"""create table as item_categories

Revision ID: 9b752f5d90e2
Revises: f1a2b3c4d5e6
Create Date: 2025-06-19 18:07:46.758677

"""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "9b752f5d90e2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "item_categories",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "uuid", UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4
        ),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column(
            "is_deleted", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP, server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.uuid"),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_table("item_categories")
