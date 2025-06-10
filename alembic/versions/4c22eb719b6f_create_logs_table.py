"""create logs table

Revision ID: 4c22eb719b6f
Revises: 79190a94e44b
Create Date: 2025-01-19 23:19:21.555398

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c22eb719b6f"
down_revision: Union[str, None] = "79190a94e44b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "logs",
        sa.Column(
            "id",
            sa.Integer(),
            sa.Identity(always=False, start=1, increment=1),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("uuid", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("entity", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("entity_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("performed_by", sa.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["performed_by"], ["users.uuid"]),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
    )


def downgrade() -> None:
    op.drop_table("logs")
