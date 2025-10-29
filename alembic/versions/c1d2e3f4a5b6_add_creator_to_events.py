"""add creator to events

Revision ID: c1d2e3f4a5b6
Revises: a1b2c3d4e5f6
Create Date: 2025-10-29 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add creator_id field to events table."""
    # Add the creator_id column (nullable initially)
    op.add_column('events',
        sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=True)
    )

    # For existing events, we can either:
    # 1. Delete them (if there are none in production)
    # 2. Set them to a default user
    # 3. Leave them null and handle in application
    # Since this is development, we'll just handle existing events
    # by setting a placeholder or requiring manual intervention

    # Create foreign key constraint
    op.create_foreign_key(
        'fk_events_creator_id_users',
        'events',
        'users',
        ['creator_id'],
        ['id']
    )

    # Create index on creator_id
    op.create_index(
        op.f('ix_events_creator_id'),
        'events',
        ['creator_id'],
        unique=False
    )

    # If you want to make it non-nullable after setting values:
    # op.alter_column('events', 'creator_id', nullable=False)


def downgrade() -> None:
    """Remove creator_id field from events table."""
    op.drop_index(op.f('ix_events_creator_id'), table_name='events')
    op.drop_constraint('fk_events_creator_id_users', 'events', type_='foreignkey')
    op.drop_column('events', 'creator_id')
