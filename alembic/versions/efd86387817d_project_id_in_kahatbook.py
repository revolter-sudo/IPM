"""project id in kahatbook

Revision ID: efd86387817d
Revises: 47d20a6965d0
Create Date: 2025-03-17 22:14:44.046005

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "efd86387817d"
down_revision: Union[str, None] = "47d20a6965d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "khatabook_entries",
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.uuid"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_constraint(
        "khatabook_entries_project_id_fkey", "khatabook_entries", type_="foreignkey"
    )
    op.drop_column("khatabook_entries", "project_id")
