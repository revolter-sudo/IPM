"""User Item Mapping

Revision ID: 7fa87240af97
Revises: 4282c81120c4
Create Date: 2025-04-26 18:45:23.481766

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '7fa87240af97'
down_revision: Union[str, None] = '4282c81120c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_item_map",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "uuid",
            UUID(as_uuid=True),
            nullable=False,
            unique=True,
            server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.uuid", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column(
            "item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("items.uuid", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column("item_balance", sa.Float, nullable=True),
        sa.UniqueConstraint(
            "user_id",
            "item_id",
            name="uq_user_item"
        )
    )


def downgrade() -> None:
    op.drop_table("user_item_map")