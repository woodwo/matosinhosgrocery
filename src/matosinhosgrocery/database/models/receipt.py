import sqlalchemy as sa
from sqlalchemy.orm import relationship

from matosinhosgrocery.database.models.base import Base, TimestampMixin

class Receipt(Base, TimestampMixin):
    __tablename__ = "receipts"

    id = sa.Column(sa.Integer, primary_key=True, index=True, autoincrement=True)
    store_name = sa.Column(sa.String, index=True)
    purchase_date = sa.Column(sa.Date, index=True)
    total_amount = sa.Column(sa.Float) # Optional, might not always be available or accurate from OCR
    
    # Link to the original scanned image/file in Google Drive
    gdrive_file_id = sa.Column(sa.String, nullable=True, unique=True)
    gdrive_file_url = sa.Column(sa.String, nullable=True) # Web link to view the file

    # Foreign key to link to a user if you implement multi-user support later
    # user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"), nullable=True, index=True)
    # user = relationship("User", back_populates="receipts")

    # Relationship to ProductItem (items on this specific receipt)
    # The ADR overview.md implies products are linked to receipts.
    # A ProductItem table might be better for many-to-many if "Product" is a global catalog item.
    # For now, let's assume a direct one-to-many from Receipt to a simplified ProductItem concept
    # or a many-to-many through an association table for generalized products.
    # Let's simplify for now: a Receipt has many ProductEntries
    product_entries = relationship("ProductEntry", back_populates="receipt", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Receipt(id={self.id}, store_name='{self.store_name}', purchase_date='{self.purchase_date}')>" 