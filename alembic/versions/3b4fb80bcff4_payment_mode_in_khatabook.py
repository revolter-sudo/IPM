"""payment_mode in khatabook

Revision ID: 3b4fb80bcff4
Revises: 78e756053030
Create Date: 2025-03-26 19:44:35.475247

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b4fb80bcff4'
down_revision: Union[str, None] = '78e756053030'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        'khatabook_entries',
        sa.Column(
            'payment_mode',
            sa.String(length=50),
            nullable=True
        )
    )


def downgrade():
    op.drop_column('khatabook_entries', 'payment_mode')
