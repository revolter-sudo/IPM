"""upi_number in person info

Revision ID: c8770a12264f
Revises: efd86387817d
Create Date: 2025-03-20 22:37:30.588281

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8770a12264f'
down_revision: Union[str, None] = 'efd86387817d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1) Add new column upi_number
    op.add_column('person', sa.Column('upi_number', sa.String(length=10), nullable=True))

    # 2) Alter columns to make them nullable
    op.alter_column(
        'person',
        'account_number',
        existing_type=sa.String(length=17),
        nullable=True
    )
    op.alter_column(
        'person',
        'ifsc_code',
        existing_type=sa.String(length=11),
        nullable=True
    )


def downgrade():
    # Reverse the above changes
    op.drop_column('person', 'upi_number')

    # op.alter_column(
    #     'person',
    #     'account_number',
    #     existing_type=sa.String(length=17),
    #     nullable=False
    # )
    # op.alter_column(
    #     'person',
    #     'ifsc_code',
    #     existing_type=sa.String(length=11),
    #     nullable=False
    # )
