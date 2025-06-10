"""Add start_date and end_date to projects

Revision ID: 1849b56b0213
Revises: c218acebaa36
Create Date: 2025-06-04 12:58:54.695205

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1849b56b0213"
down_revision: Union[str, None] = "c218acebaa36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("projects", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("projects", sa.Column("end_date", sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("projects", "start_date")
    op.drop_column("projects", "end_date")
