"""PaymentStatusHistory Table

Revision ID: 9601c81cc8fe
Revises: c5b4b232f141
Create Date: 2025-03-02 23:57:18.192080

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9601c81cc8fe"
down_revision: Union[str, None] = "c5b4b232f141"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "payment_status_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "payment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("payments.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.uuid"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    # Optionally, you can add a unique constraint on 'uuid'
    op.create_unique_constraint(
        "uq_payment_status_history_uuid", "payment_status_history", ["uuid"]
    )


def downgrade():
    # Drops the table and its constraints
    op.drop_constraint(
        "uq_payment_status_history_uuid", "payment_status_history", type_="unique"
    )
    op.drop_table("payment_status_history")
