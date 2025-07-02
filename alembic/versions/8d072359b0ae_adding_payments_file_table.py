"""adding payments file table

Revision ID: 8d072359b0ae
Revises: 8b77d13f892f
Create Date: 2025-02-27 01:54:18.479643

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8d072359b0ae"
down_revision: Union[str, None] = "8b77d13f892f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Remove the 'file' column from 'payments' table
    op.drop_column("payments", "file")

    # Create the 'payment_files' table
    op.create_table(
        "payment_files",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "payment_id",
            UUID(as_uuid=True),
            sa.ForeignKey("payments.uuid"),
            nullable=False,
        ),
        sa.Column("file_path", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP, server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade():
    # Add back the 'file' column in 'payments' table
    op.add_column("payments", sa.Column("file", sa.String(255), nullable=True))

    # Drop the 'payment_files' table
    op.drop_table("payment_files")
