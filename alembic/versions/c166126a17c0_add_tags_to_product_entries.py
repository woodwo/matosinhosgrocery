"""add_tags_to_product_entries

Revision ID: c166126a17c0
Revises: 7a5042c6a307
Create Date: 2025-05-17 21:31:02.846356

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite  # Import for sqlite.JSON


# revision identifiers, used by Alembic.
revision: str = "c166126a17c0"
down_revision: Union[str, None] = "7a5042c6a307"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("product_entries", sa.Column("tags", sqlite.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("product_entries", "tags")
