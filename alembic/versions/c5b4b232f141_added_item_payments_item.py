"""added item payments_item

Revision ID: c5b4b232f141
Revises: 60c26db94462
Create Date: 2025-02-27 21:30:02.341989

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5b4b232f141'
down_revision: Union[str, None] = '60c26db94462'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Create the items table
    op.create_table(
        "items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("uuid", UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),  # Category is optional
    )

    # Create the payment_items table for many-to-many mapping
    op.create_table(
        "payment_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("payment_id", UUID(as_uuid=True), sa.ForeignKey("payments.uuid", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", UUID(as_uuid=True), sa.ForeignKey("items.uuid", ondelete="CASCADE"), nullable=False),
    )


def downgrade():
    # Drop tables in reverse order
    op.drop_table("payment_items")
    op.drop_table("items")
