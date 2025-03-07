"""khatabook balance table

Revision ID: cd015e5f3e41
Revises: b79434f5a12d
Create Date: 2025-03-06 22:06:17.599767

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa
import uuid


# revision identifiers, used by Alembic.
revision: str = 'cd015e5f3e41'
down_revision: Union[str, None] = 'b79434f5a12d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "khatabook_balance",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("uuid", UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4),
        sa.Column("user_uuid", UUID(as_uuid=True), sa.ForeignKey("users.uuid"), nullable=False, unique=True),
        sa.Column("balance", sa.Float, nullable=False, default=0.0),
    )


def downgrade():
    op.drop_table("khatabook_balance")
