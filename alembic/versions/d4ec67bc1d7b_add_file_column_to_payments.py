"""Add file column to payments

Revision ID: d4ec67bc1d7b
Revises: e84c1ee63ab4
Create Date: 2025-01-19 23:25:09.584238

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4ec67bc1d7b"
down_revision: Union[str, None] = "e84c1ee63ab4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("file", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("payments", "file")
