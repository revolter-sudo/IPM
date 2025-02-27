"""Add parent_id to person table

Revision ID: 60c26db94462
Revises: 8d072359b0ae
Create Date: 2025-02-27 12:06:11.331397

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60c26db94462'
down_revision: Union[str, None] = '8d072359b0ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add parent_id column to support parent-child accounts
    op.add_column("person", sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("person.uuid"), nullable=True))


def downgrade():
    # Remove parent_id column in case of rollback
    op.drop_column("person", "parent_id")
