"""balance after netry

Revision ID: 0088460af7ec
Revises: f94cb9f3b976
Create Date: 2025-03-12 23:47:27.561565

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0088460af7ec'
down_revision: Union[str, None] = 'f94cb9f3b976'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "khatabook_entries",
        sa.Column("balance_after_entry", sa.Float, nullable=True)
    )


def downgrade():
    op.drop_column("khatabook_entries", "balance_after_entry")
