"""add_project_balances_and_invoice_model

Revision ID: 4282c81120c4
Revises: 2acae3179ba4
Create Date: 2025-04-26 01:44:07.211080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '4282c81120c4'
down_revision: Union[str, None] = '2acae3179ba4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns to Project table
    op.add_column('projects', sa.Column('po_balance', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('projects', sa.Column('estimated_balance', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('projects', sa.Column('actual_balance', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('projects', sa.Column('po_document_path', sa.String(255), nullable=True))

    # 2. Add balance_type column to project_balances table
    op.add_column('project_balances', sa.Column('balance_type', sa.String(20), nullable=False, server_default='actual'))

    # 3. Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('uuid', UUID(), nullable=False, unique=True),
        sa.Column('project_id', UUID(), sa.ForeignKey('projects.uuid'), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='uploaded'),
        sa.Column('created_by', UUID(), sa.ForeignKey('users.uuid'), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )

    # Create indexes
    op.create_index('idx_invoices_project_id', 'invoices', ['project_id'])
    op.create_index('idx_invoices_created_by', 'invoices', ['created_by'])


def downgrade() -> None:
    # 1. Drop invoices table
    op.drop_index('idx_invoices_created_by', 'invoices')
    op.drop_index('idx_invoices_project_id', 'invoices')
    op.drop_table('invoices')

    # 2. Remove balance_type column from project_balances
    op.drop_column('project_balances', 'balance_type')

    # 3. Remove new columns from Project table
    op.drop_column('projects', 'po_document_path')
    op.drop_column('projects', 'actual_balance')
    op.drop_column('projects', 'estimated_balance')
    op.drop_column('projects', 'po_balance')
