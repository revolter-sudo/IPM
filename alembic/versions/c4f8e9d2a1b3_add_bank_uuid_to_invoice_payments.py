"""add_bank_uuid_to_invoice_payments

Revision ID: c4f8e9d2a1b3
Revises: b1d8a8032831
Create Date: 2023-10-10 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

# revision identifiers, used by Alembic.
revision = 'c4f8e9d2a1b3'
down_revision : Union[str, None, Sequence[str]]= 'b1d8a8032831'
branch_labels = None
depends_on = None


def upgrade():
    # Add bank_uuid column to invoice_payments table
    op.add_column(
        'invoice_payments',
        sa.Column(
            'bank_uuid',
            UUID(as_uuid=True),
            sa.ForeignKey('balance_details.uuid'),
            nullable=True
        )
    )


def downgrade():
    # Remove bank_uuid column from invoice_payments table
    op.drop_column('invoice_payments', 'bank_uuid')
