"""removed phone constraint and allow person characters

Revision ID: e193c436ccf7
Revises: 549571b97cc9
Create Date: 2025-04-04 23:51:17.371505

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e193c436ccf7'
down_revision: Union[str, None] = '549571b97cc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1) Remove the unique constraint from users.phone
    #    If alembic autogenerate named it "users_phone_key" (common in Postgres),
    #    drop that constraint name. You can check via `\d+ users` in psql or an autogenerate script.
    op.drop_constraint('users_phone_key', 'users', type_='unique')
    op.alter_column('users', 'phone',
                    existing_type=sa.BigInteger(),
                    nullable=False
                    )

    # 2) Change the person.name column length to 500
    op.alter_column(
        'person', 'name',
        existing_type=sa.String(length=25),
        type_=sa.String(length=500),
        nullable=False
    )


def downgrade():
    # 1) Re-add the unique constraint to users.phone
    op.create_unique_constraint('users_phone_key', 'users', ['phone'])
    op.alter_column('users', 'phone',
                    existing_type=sa.BigInteger(),
                    nullable=False
                    )

    # 2) Revert the person.name column length back to 25
    op.alter_column(
        'person', 'name',
        existing_type=sa.String(length=500),
        type_=sa.String(length=25),
        nullable=False
    )
