"""add_gdrive_filename_to_receipts

Revision ID: 7b7f2cb32eb2
Revises: c763dfcfd72a
Create Date: 2025-05-17 21:45:15.718535

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7b7f2cb32eb2"
down_revision: Union[str, None] = "c763dfcfd72a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("receipts", sa.Column("gdrive_filename", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("receipts", "gdrive_filename")
