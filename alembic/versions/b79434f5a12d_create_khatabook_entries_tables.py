"""Create Khatabook entries tables

Revision ID: b79434f5a12d
Revises: 7c74867c848f
Create Date: 2025-03-05 20:08:38.010645

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b79434f5a12d"
down_revision: Union[str, None] = "7c74867c848f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "khatabook_entries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "uuid", UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4
        ),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("remarks", sa.Text, nullable=True),
        sa.Column(
            "person_id", UUID(as_uuid=True), sa.ForeignKey("person.uuid"), nullable=True
        ),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.uuid"), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
    )

    op.create_table(
        "khatabook_files",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("khatabook_id", UUID(as_uuid=True), nullable=False),
        sa.Column("file_path", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_khatabook_files_khatabook_id",
        source_table="khatabook_files",
        referent_table="khatabook_entries",
        local_cols=["khatabook_id"],
        remote_cols=["uuid"],
        ondelete="CASCADE",
    )

    op.create_table(
        "khatabook_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("khatabook_id", UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", UUID(as_uuid=True), nullable=False),
    )
    op.create_foreign_key(
        "fk_khatabook_items_khatabook_id",
        source_table="khatabook_items",
        referent_table="khatabook_entries",
        local_cols=["khatabook_id"],
        remote_cols=["uuid"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_khatabook_items_item_id",
        source_table="khatabook_items",
        referent_table="items",
        local_cols=["item_id"],
        remote_cols=["uuid"],
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_table("khatabook_items")
    op.drop_table("khatabook_files")
    op.drop_table("khatabook_entries")
