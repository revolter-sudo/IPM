"""project user and item mapping

Revision ID: a204f977ee2a
Revises: 124e3c693cc9
Create Date: 2025-04-19 13:58:55.553006

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects.postgresql import UUID
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a204f977ee2a'
down_revision: Union[str, None] = '124e3c693cc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- project_user_map ----------------------------------------------------
    op.create_table(
        "project_user_map",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "uuid",
            UUID(as_uuid=True),
            nullable=False,
            unique=True,
            server_default=sa.text("gen_random_uuid()"),   # ← pg ≥13, or swap for uuid_generate_v4()
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id",
            "project_id",
            name="uq_user_project",
        ),
    )

    # --- project_item_map ----------------------------------------------------
    op.create_table(
        "project_item_map",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "uuid",
            UUID(as_uuid=True),
            nullable=False,
            unique=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("items.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("project_item_map")
    op.drop_table("project_user_map")
