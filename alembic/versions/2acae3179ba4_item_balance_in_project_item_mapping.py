"""item balance in project item mapping

Revision ID: 2acae3179ba4
Revises: e384ec734894
Create Date: 2025-04-25 19:56:37.365972

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2acae3179ba4'
down_revision: Union[str, None] = 'e384ec734894'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'project_item_map',
        sa.Column("item_balance", sa.Float, nullable=False, server_default="0.0")
    )


def downgrade() -> None:
    op.drop_column(
        'project_item_map',
        'item_balance'
    )
