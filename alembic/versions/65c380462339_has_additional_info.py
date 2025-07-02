"""has_additional_info

Revision ID: 65c380462339
Revises: e193c436ccf7
Create Date: 2025-04-05 01:31:47.034862

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "65c380462339"
down_revision: Union[str, None] = "e193c436ccf7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "items",
        sa.Column(
            "has_additional_info",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # Optional step to drop the server_default if you don’t want it perpetually on the column
    op.alter_column("items", "has_additional_info", server_default=None)


def downgrade():
    op.drop_column("items", "has_additional_info")
