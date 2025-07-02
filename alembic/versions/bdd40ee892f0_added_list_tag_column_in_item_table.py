"""added list_tag column in item table

Revision ID: bdd40ee892f0
Revises: 37b02a0f4dbe
Create Date: 2025-03-23 21:14:10.799686

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bdd40ee892f0"
down_revision: Union[str, None] = "37b02a0f4dbe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("items", sa.Column("list_tag", sa.String(length=30), nullable=True))


def downgrade():
    op.drop_column("items", "list_tag")
