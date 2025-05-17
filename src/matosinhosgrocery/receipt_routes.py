import logging
from typing import Optional, List
import os

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession

from matosinhosgrocery.services.receipt_processing_service import (
    ReceiptProcessingService,
)
from matosinhosgrocery.database.connection import get_async_db_session
from matosinhosgrocery.schemas.receipt_schemas import ReceiptResponse, ProductResponse
from matosinhosgrocery.database.models import Receipt as DBReceipt

logger = logging.getLogger(__name__)
receipt_api_router = APIRouter()  # This is the router instance


def convert_db_receipt_to_response(db_receipt: DBReceipt) -> ReceiptResponse:
    """Converts a SQLAlchemy Receipt model to a ReceiptResponse Pydantic model."""
    product_responses: List[ProductResponse] = []
    if db_receipt.product_entries:
        for entry in db_receipt.product_entries:
            product_responses.append(
                ProductResponse(
                    name=entry.original_name,
                    generalized_name=entry.generalized_name,
                    cost=entry.price_per_unit,
                    tags=entry.tags if entry.tags else [],
                )
            )

    return ReceiptResponse(
        file_name=db_receipt.gdrive_filename if db_receipt.gdrive_filename else "N/A",
        gdrive_url=db_receipt.gdrive_file_url,
        products=product_responses,
    )


@receipt_api_router.post("/receipts/upload", response_model=ReceiptResponse)
async def upload_receipt_file(
    file: UploadFile = File(...),
    original_file_name: Optional[str] = Form(None),
    user_identifier: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_db_session),
) -> ReceiptResponse:
    """
    Uploads a receipt file (image or PDF) for processing.
    This endpoint uses the application's real OpenAI and Google Drive clients.
    Returns structured receipt data including product details.
    """
    logger.info(
        f"API /receipts/upload called. File: {file.filename}, User: {user_identifier}, Original Form Filename: {original_file_name}"
    )

    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Determine the filename to be used by the service, prioritizing a name with a proper extension.
    # This name is primarily used by the service to derive the original extension for GDrive naming.
    service_input_filename: str
    if (
        original_file_name and "." in original_file_name
    ):  # User provided a name with an extension
        service_input_filename = original_file_name
    elif (
        file.filename and "." in file.filename
    ):  # Uploaded file has a name with an extension
        service_input_filename = file.filename
    elif original_file_name:  # User provided a name, but no extension
        # Try to append extension from actual uploaded filename if available
        _, ext_from_upload = os.path.splitext(file.filename if file.filename else "")
        if ext_from_upload:
            service_input_filename = original_file_name + ext_from_upload
            logger.info(
                f"Appended extension '{ext_from_upload}' to user-provided filename '{original_file_name}'. New input filename: '{service_input_filename}'"
            )
        else:
            service_input_filename = original_file_name  # No extension found anywhere, service might default to .dat via filename_utils
            logger.warning(
                f"No extension found for user-provided filename '{original_file_name}' or uploaded file. Filename utils might default to .dat."
            )
    elif file.filename:  # No user-provided name, use uploaded filename
        service_input_filename = file.filename
    else:  # No names available at all
        logger.error(
            "Filename could not be determined from API input (no original_file_name, no file.filename)."
        )
        raise HTTPException(
            status_code=400,
            detail="Filename could not be determined. Please provide 'original_file_name' or ensure the uploaded file has a name.",
        )

    if not service_input_filename:
        # This case should ideally be caught by the logic above, but as a failsafe:
        logger.error(
            "Critical: service_input_filename is empty after determination logic."
        )
        raise HTTPException(
            status_code=500, detail="Internal error determining input filename."
        )

    # Instantiate the service. Since this path doesn't use bot's download,
    # passing bot_instance=None is acceptable due to our refactoring.
    receipt_service = ReceiptProcessingService(db_session=db, bot_instance=None)

    try:
        processed_db_receipt: DBReceipt = (
            await receipt_service.process_receipt_from_uploaded_file(
                file_content=file_content,
                original_file_name=service_input_filename,
                user_identifier=user_identifier,
            )
        )
        # Convert SQLAlchemy model to Pydantic response model
        return convert_db_receipt_to_response(processed_db_receipt)

    except ValueError as ve:
        logger.error(
            f"ValueError during API receipt processing for {service_input_filename}: {ve}",
            exc_info=True,
        )
        raise HTTPException(status_code=400, detail=str(ve))
    except (
        RuntimeError
    ) as re:  # For errors like bot instance missing when it shouldn't be
        logger.error(
            f"RuntimeError during API receipt processing for {service_input_filename}: {re}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        logger.error(
            f"Unexpected error during API receipt processing for {service_input_filename}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"An unexpected server error occurred: {str(e)}"
        )
