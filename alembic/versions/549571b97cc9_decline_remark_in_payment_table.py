"""decline remark in payment table

Revision ID: 549571b97cc9
Revises: e88faeeccc58
Create Date: 2025-04-03 00:27:23.494666

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "549571b97cc9"
down_revision: Union[str, None] = "e88faeeccc58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "payments",
        sa.Column("decline_remark", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_column("payments", "decline_remark")
