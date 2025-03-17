"""remove user_id from khatabook table

Revision ID: b4d087e09e89
Revises: 51aaa6e32568
Create Date: 2025-03-09 20:33:51.522781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4d087e09e89'
down_revision: Union[str, None] = '51aaa6e32568'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Remove the `user_id` column from `khatabook_entries`
    op.drop_column("khatabook_entries", "user_id")

    # Add the `expense_date` column to `khatabook_entries`
    op.add_column("khatabook_entries", sa.Column(
        "expense_date",
        sa.TIMESTAMP(),
        nullable=True)
    )


def downgrade():
    # Re-add the `user_id` column if we need to rollback
    op.add_column(
        "khatabook_entries",
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.uuid"),
            nullable=True
        )
    )

    # Remove the `expense_date` column if we need to rollback
    op.drop_column("khatabook_entries", "expense_date")
