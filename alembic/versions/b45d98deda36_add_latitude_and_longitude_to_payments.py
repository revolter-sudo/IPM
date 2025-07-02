"""Add latitude and longitude to payments

Revision ID: b45d98deda36
Revises: f606c0deb93e
Create Date: 2025-03-04 22:29:48.224122

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b45d98deda36"
down_revision: Union[str, None] = "f606c0deb93e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # If you want them required but have existing data, you need a default.
    # Example: server_default="0"
    op.add_column(
        "payments",
        sa.Column("latitude", sa.Float(), nullable=False, server_default="23.022505"),
    )
    op.add_column(
        "payments",
        sa.Column("longitude", sa.Float(), nullable=False, server_default="72.571365"),
    )
    # If you do not want to set a default, remove server_default and set them to nullable=True
    # then do a data migration separately.


def downgrade():
    op.drop_column("payments", "longitude")
    op.drop_column("payments", "latitude")
