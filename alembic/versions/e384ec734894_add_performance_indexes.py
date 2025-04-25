"""add_performance_indexes

Revision ID: e384ec734894
Revises: a204f977ee2a
Create Date: 2025-04-23 19:12:24.203252

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e384ec734894'
down_revision: Union[str, None] = 'a204f977ee2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Common condition for partial indexes
    not_deleted = sa.text("is_deleted = false")

    # Add indexes for frequently filtered columns in payments table
    op.create_index(
        'idx_payment_status',
        'payments',
        ['status'],
        postgresql_where=not_deleted
    )
    op.create_index(
        'idx_payment_created_by',
        'payments',
        ['created_by'],
        postgresql_where=not_deleted
    )
    op.create_index(
        'idx_payment_created_at',
        'payments',
        ['created_at'],
        postgresql_where=not_deleted
    )
    op.create_index(
        'idx_payment_project_id',
        'payments',
        ['project_id'],
        postgresql_where=not_deleted
    )

    # Add indexes for frequently filtered columns in other tables
    op.create_index('idx_person_is_deleted', 'person', ['is_deleted'])
    op.create_index('idx_project_is_deleted', 'projects', ['is_deleted'])

    # Composite indexes for common query patterns
    op.create_index(
        'idx_payment_status_created_at',
        'payments',
        ['status', 'created_at'],
        postgresql_where=not_deleted
    )
    op.create_index(
        'idx_payment_created_by_status',
        'payments',
        ['created_by', 'status'],
        postgresql_where=not_deleted
    )


def downgrade() -> None:
    # Drop all indexes created in upgrade
    op.drop_index('idx_payment_status', table_name='payments')
    op.drop_index('idx_payment_created_by', table_name='payments')
    op.drop_index('idx_payment_created_at', table_name='payments')
    op.drop_index('idx_payment_project_id', table_name='payments')
    op.drop_index('idx_person_is_deleted', table_name='person')
    op.drop_index('idx_project_is_deleted', table_name='projects')
    op.drop_index('idx_payment_status_created_at', table_name='payments')
    op.drop_index('idx_payment_created_by_status', table_name='payments')
