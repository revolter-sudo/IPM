"""add created_at in users projects and items

Revision ID: 3160faadbcc2
Revises: 7ad08b83b1fc
Create Date: 2025-06-16 11:34:45.041374

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "3160faadbcc2"
down_revision = "7ad08b83b1fc"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "projects",
        sa.Column(
            "created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False
        ),
    )
    op.add_column(
        "items",
        sa.Column(
            "created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade():
    op.drop_column("projects", "created_at")
    op.drop_column("users", "created_at")
    op.drop_column("items", "created_at")
