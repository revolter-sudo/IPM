"""create projects table

Revision ID: 1040202fa450
Revises: ede455653854
Create Date: 2025-01-19 23:14:23.333140

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1040202fa450"
down_revision: Union[str, None] = "ede455653854"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column(
            "id",
            sa.Integer(),
            sa.Identity(always=False, start=1, increment=1),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("uuid", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
    )


def downgrade() -> None:
    op.drop_table("projects")
