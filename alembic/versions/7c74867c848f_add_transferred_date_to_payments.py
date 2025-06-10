"""Add transferred_date to payments

Revision ID: 7c74867c848f
Revises: b45d98deda36
Create Date: 2025-03-04 23:00:15.318326

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c74867c848f"
down_revision: Union[str, None] = "b45d98deda36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "payments",
        sa.Column("transferred_date", sa.TIMESTAMP(), nullable=True),
    )


def downgrade():
    op.drop_column("payments", "transferred_date")
