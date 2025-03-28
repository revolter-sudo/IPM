"""balance table

Revision ID: 78e756053030
Revises: bdd40ee892f0
Create Date: 2025-03-24 19:41:06.825237

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78e756053030'
down_revision: Union[str, None] = 'bdd40ee892f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'balance_details',
        sa.Column(
            'id',
            sa.Integer(),
            sa.Identity(always=False, start=1, increment=1),
            primary_key=True,
            nullable=False
        ),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('balance', sa.Float, nullable=False),
    )


def downgrade():
    op.drop_table('balance_details')
