"""enable_postgis_extension

Revision ID: 7f493d6ede7c
Revises: 
Create Date: 2025-10-29 15:36:41.239340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f493d6ede7c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable PostGIS extension for geospatial support."""
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")


def downgrade() -> None:
    """Disable PostGIS extension."""
    op.execute("DROP EXTENSION IF EXISTS postgis")
