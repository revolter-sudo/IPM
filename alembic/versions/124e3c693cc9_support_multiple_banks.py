"""support multiple banks

Revision ID: 124e3c693cc9
Revises: b36ded34d38b
Create Date: 2025-04-16 14:24:25.143254

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '124e3c693cc9'
down_revision: Union[str, None] = 'b36ded34d38b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1) Add 'name' column to balance_details
    op.add_column(
        "balance_details",
        sa.Column("name", sa.String(255), nullable=False, server_default="Bank_1")
    )
    # Remove the default now that the column is created
    op.alter_column("balance_details", "name", server_default=None)

    # 2) Add 'deducted_from_bank_uuid' to payments
    op.add_column(
        "payments",
        sa.Column(
            "deducted_from_bank_uuid",
            UUID(as_uuid=True),
            nullable=True
        ),
    )

    # 3) Create a foreign key from payments(deducted_from_bank_uuid) → balance_details(uuid)
    op.create_foreign_key(
        "fk_payments_balance_details",
        source_table="payments",
        referent_table="balance_details",
        local_cols=["deducted_from_bank_uuid"],
        remote_cols=["uuid"],
    )


def downgrade():
    op.drop_constraint("fk_payments_balance_details", "payments", type_="foreignkey")
    op.drop_column("payments", "deducted_from_bank_uuid")
    op.drop_column("balance_details", "name")
