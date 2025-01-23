"""add persons table reference in payments table

Revision ID: 0ec6254abeca
Revises: aa41d666c45f
Create Date: 2025-01-21 15:47:51.499859

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0ec6254abeca'
down_revision: Union[str, None] = 'aa41d666c45f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the 'person' column
    op.add_column(
        'payments',
        sa.Column('person', UUID(as_uuid=True), nullable=True)
    )
    # Add foreign key constraint for the 'person' column
    op.create_foreign_key(
        'fk_payments_person',  # Constraint name
        'payments',            # Source table
        'person',              # Target table
        ['person'],            # Source column(s)
        ['uuid']               # Target column(s)
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint('fk_payments_person', 'payments', type_='foreignkey')
    # Remove the 'person' column
    op.drop_column('payments', 'person')
