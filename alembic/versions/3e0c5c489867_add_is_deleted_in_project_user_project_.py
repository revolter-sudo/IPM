"""add is_deleted in project user project item and project user item table

Revision ID: 3e0c5c489867
Revises: 9b752f5d90e2
Create Date: 2025-06-20 13:18:24.993039

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "3e0c5c489867"
down_revision = "9b752f5d90e2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("project_user_map") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )

    with op.batch_alter_table("project_item_map") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )

    with op.batch_alter_table("project_user_item_map") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )


def downgrade():
    with op.batch_alter_table("project_user_map") as batch_op:
        batch_op.drop_column("is_deleted")

    with op.batch_alter_table("project_item_map") as batch_op:
        batch_op.drop_column("is_deleted")

    with op.batch_alter_table("project_user_item_map") as batch_op:
        batch_op.drop_column("is_deleted")
