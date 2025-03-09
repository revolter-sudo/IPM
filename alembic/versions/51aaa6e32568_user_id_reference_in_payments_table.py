"""user id reference in payments table

Revision ID: 51aaa6e32568
Revises: dba5cabc9602
Create Date: 2025-03-09 17:15:04.278613

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51aaa6e32568'
down_revision: Union[str, None] = 'dba5cabc9602'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add the `user_id` column to the `person` table
    op.add_column(
        "person",
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.uuid"),
            unique=True, nullable=True
        ),
    )


def downgrade():
    # Remove the `user_id` column if we need to rollback
    op.drop_column("person", "user_id")
