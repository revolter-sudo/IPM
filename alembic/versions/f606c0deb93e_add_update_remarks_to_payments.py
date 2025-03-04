"""Add update_remarks to payments

Revision ID: f606c0deb93e
Revises: 9601c81cc8fe
Create Date: 2025-03-04 21:47:11.587172

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f606c0deb93e'
down_revision: Union[str, None] = '9601c81cc8fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "payments",
        sa.Column("update_remarks", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_column("payments", "update_remarks")
