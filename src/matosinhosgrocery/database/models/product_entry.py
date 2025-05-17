import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON

from matosinhosgrocery.database.models.base import Base, TimestampMixin


class ProductEntry(Base, TimestampMixin):
    __tablename__ = "product_entries"

    id = sa.Column(sa.Integer, primary_key=True, index=True, autoincrement=True)

    # Information extracted directly from the receipt for this specific entry
    original_name = sa.Column(
        sa.String, nullable=False, index=True
    )  # As it appears on the receipt
    generalized_name = sa.Column(
        sa.String, nullable=False, index=True
    )  # AI-processed name
    tags = sa.Column(JSON, nullable=True)

    price_per_unit = sa.Column(sa.Float, nullable=False)
    quantity = sa.Column(
        sa.Float, default=1.0, nullable=False
    )  # e.g., 1, 2, 0.5 (for kg)

    weight_volume_text = sa.Column(
        sa.String, nullable=True
    )  # e.g., "120g", "1L", as text from receipt
    # You might add parsed weight/volume later if needed:
    parsed_weight_grams = sa.Column(sa.Float, nullable=True)
    parsed_volume_ml = sa.Column(sa.Float, nullable=True)

    # Foreign key to link to the Receipt this entry belongs to
    receipt_id = sa.Column(
        sa.Integer, sa.ForeignKey("receipts.id"), nullable=False, index=True
    )
    receipt = relationship("Receipt", back_populates="product_entries")

    # Potential link to a global "Product" catalog if you build one later
    # global_product_id = sa.Column(sa.Integer, sa.ForeignKey("global_products.id"), nullable=True, index=True)
    # global_product = relationship("GlobalProduct", back_populates="receipt_entries")

    def __repr__(self):
        return (
            f"<ProductEntry(id={self.id}, original_name='{self.original_name}', "
            f"price={self.price_per_unit}, quantity={self.quantity}, receipt_id={self.receipt_id})>"
        )
