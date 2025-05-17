"""add_parsed_weight_volume_to_product_entries

Revision ID: c763dfcfd72a
Revises: c166126a17c0
Create Date: 2025-05-17 21:39:41.077405

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c763dfcfd72a"
down_revision: Union[str, None] = "c166126a17c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "product_entries", sa.Column("parsed_weight_grams", sa.Float(), nullable=True)
    )
    op.add_column(
        "product_entries", sa.Column("parsed_volume_ml", sa.Float(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("product_entries", "parsed_volume_ml")
    op.drop_column("product_entries", "parsed_weight_grams")
