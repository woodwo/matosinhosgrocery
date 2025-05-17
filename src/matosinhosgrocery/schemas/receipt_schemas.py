from typing import List, Optional
from pydantic import BaseModel, HttpUrl


class ProductResponse(BaseModel):
    """
    Response model for a single product item.
    """

    name: str
    generalized_name: str
    cost: Optional[float] = None  # Assuming cost is price_per_unit
    tags: List[str] = []

    class Config:
        orm_mode = True  # For compatibility with SQLAlchemy models


class ReceiptResponse(BaseModel):
    """
    Response model for a processed receipt.
    """

    file_name: str  # Corresponds to gdrive_filename
    gdrive_url: Optional[HttpUrl] = None
    products: List[ProductResponse] = []

    class Config:
        orm_mode = True  # For compatibility with SQLAlchemy models


# Example of how these models might be populated from your service's DB models:
#
# from matosinhosgrocery.database.models import Receipt as DBReceipt
#
# def convert_db_receipt_to_response(db_receipt: DBReceipt) -> ReceiptResponse:
#     product_responses = []
#     if db_receipt.product_entries:
#         for entry in db_receipt.product_entries:
#             product_responses.append(
#                 ProductResponse(
#                     name=entry.original_name,
#                     generalized_name=entry.generalized_name,
#                     cost=entry.price_per_unit,
#                     tags=entry.tags if entry.tags else []
#                 )
#             )
#
#     return ReceiptResponse(
#         file_name=db_receipt.gdrive_filename,
#         gdrive_url=db_receipt.gdrive_file_url,
#         products=product_responses
#     )
