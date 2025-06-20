"""add_invoice_fields_simple

Revision ID: c218acebaa36
Revises: add_default_config_table
Create Date: 2025-05-31 03:06:07.095371

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c218acebaa36'
down_revision: Union[str, None] = 'add_default_config_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to invoices table
    op.add_column('invoices', sa.Column(
        'client_name', sa.String(length=255), nullable=False, server_default=''
    ))
    op.add_column('invoices', sa.Column(
        'invoice_item', sa.String(length=255), nullable=False,
        server_default=''
    ))
    op.add_column('invoices', sa.Column(
        'due_date', sa.TIMESTAMP(), nullable=False,
        server_default=sa.func.now()
    ))

    # Remove server defaults after adding columns
    op.alter_column('invoices', 'client_name', server_default=None)
    op.alter_column('invoices', 'invoice_item', server_default=None)
    op.alter_column('invoices', 'due_date', server_default=None)


def downgrade() -> None:
    # Remove the added columns
    op.drop_column('invoices', 'due_date')
    op.drop_column('invoices', 'invoice_item')
    op.drop_column('invoices', 'client_name')
