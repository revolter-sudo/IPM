"""added self to payments table

Revision ID: f590bba3f9aa
Revises: cd015e5f3e41
Create Date: 2025-03-06 22:32:09.846979

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f590bba3f9aa"
down_revision: Union[str, None] = "cd015e5f3e41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "payments",
        sa.Column(
            "self_payment",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade():
    op.drop_column("payments", "self_payment")
