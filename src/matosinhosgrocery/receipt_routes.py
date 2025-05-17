import logging
from typing import Optional

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession

from matosinhosgrocery.services.receipt_processing_service import ReceiptProcessingService
from matosinhosgrocery.database.connection import get_async_db_session
# from matosinhosgrocery.database.models import Receipt # For Pydantic model if you create one

logger = logging.getLogger(__name__)
receipt_api_router = APIRouter() # This is the router instance

@receipt_api_router.post("/receipts/upload", response_model=None) # Define Pydantic model later
async def upload_receipt_file(
    file: UploadFile = File(...),
    original_file_name: Optional[str] = Form(None),
    user_identifier: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_db_session),
):
    logger.info(f"API /receipts/upload called. File: {file.filename}, User: {user_identifier}")
    
    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    effective_filename = original_file_name or file.filename
    if not effective_filename:
        raise HTTPException(status_code=400, detail="Filename could not be determined. Please provide 'original_file_name' or ensure the uploaded file has a name.")

    # Instantiate the service. Since this path doesn't use bot's download,
    # passing bot_instance=None is acceptable due to our refactoring.
    receipt_service = ReceiptProcessingService(db_session=db, bot_instance=None)

    try:
        processed_receipt = await receipt_service.process_receipt_from_uploaded_file(
            file_content=file_content,
            original_file_name=effective_filename,
            user_identifier=user_identifier
        )
        # For a proper API, convert SQLAlchemy model to a Pydantic model for the response
        # For now, returning a dict.
        return {
            "id": processed_receipt.id,
            "store_name": processed_receipt.store_name,
            "purchase_date": str(processed_receipt.purchase_date) if processed_receipt.purchase_date else None,
            "total_amount": processed_receipt.total_amount,
            "gdrive_file_id": processed_receipt.gdrive_file_id,
            "gdrive_file_url": processed_receipt.gdrive_file_url,
            "product_entries_count": len(processed_receipt.product_entries),
            "message": "Receipt processed successfully."
        }
    except ValueError as ve:
        logger.error(f"ValueError during API receipt processing for {effective_filename}: {ve}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re: # For errors like bot instance missing when it shouldn't be
        logger.error(f"RuntimeError during API receipt processing for {effective_filename}: {re}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        logger.error(f"Unexpected error during API receipt processing for {effective_filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}") 