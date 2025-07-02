"""create item_group_map table

Revision ID: d92f2734cb12
Revises: 96ebbf697ff8
Create Date: 2025-06-23 12:39:49.636383

"""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "d92f2734cb12"
down_revision = "96ebbf697ff8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "item_group_map",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "uuid", UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4
        ),
        sa.Column(
            "item_group_id",
            UUID(as_uuid=True),
            sa.ForeignKey("item_groups.uuid"),
            nullable=False,
        ),
        sa.Column(
            "item_id", UUID(as_uuid=True), sa.ForeignKey("items.uuid"), nullable=False
        ),
        sa.Column("item_balance", sa.Float(), nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )


def downgrade():
    op.drop_table("item_group_map")
