"""add password field to user

Revision ID: a1b2c3d4e5f6
Revises: b1c2d3e4f5a6
Create Date: 2025-10-29 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add hashed_password field to users table."""
    # Add the password field - since existing users may exist,
    # we need to handle this carefully
    op.add_column('users',
        sa.Column('hashed_password', sa.String(length=255), nullable=True)
    )

    # For existing users, set a temporary password hash
    # In production, you would handle this differently (notify users to reset password)
    op.execute("UPDATE users SET hashed_password = 'TEMP_HASH_REQUIRE_PASSWORD_RESET' WHERE hashed_password IS NULL")

    # Now make it non-nullable
    op.alter_column('users', 'hashed_password', nullable=False)


def downgrade() -> None:
    """Remove hashed_password field from users table."""
    op.drop_column('users', 'hashed_password')
