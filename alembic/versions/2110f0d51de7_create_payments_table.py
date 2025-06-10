"""create payments table

Revision ID: 2110f0d51de7
Revises: 1040202fa450
Create Date: 2025-01-19 23:15:30.707654

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2110f0d51de7"
down_revision: Union[str, None] = "1040202fa450"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column(
            "id",
            sa.Integer(),
            sa.Identity(always=False, start=1, increment=1),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("uuid", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("project_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.uuid"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.uuid"]),
    )


def downgrade() -> None:
    op.drop_table("payments")
