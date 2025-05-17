import logging
import datetime  # For placeholder data and date parsing
import asyncio  # Added asyncio
import mimetypes  # For inferring mime types
import os  # Added for os.path.splitext
from typing import Tuple, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Bot  # Import Bot for type hinting

# from telegram.ext import Application # No longer needed here for global_bot_app

from matosinhosgrocery.database.models import Receipt, ProductEntry

# We will need CRUD operations later, let's anticipate their module
# from matosinhosgrocery.database.crud import receipt_crud, product_entry_crud

# Import the actual OpenAI client function
from matosinhosgrocery.external_apis.openai_client import (
    extract_receipt_data_from_image,
)
from matosinhosgrocery.external_apis.google_drive_client import (
    upload_file_to_gdrive,
)  # Added

# Placeholder for external API client modules
# from matosinhosgrocery.external_apis.openai_client import extract_receipt_data
# from matosinhosgrocery.external_apis.gdrive_client import upload_receipt_to_gdrive # Removed comment

# from matosinhosgrocery.bot.core import bot_app as global_bot_app # Remove global import

# NEW: Import filename generation utilities
from matosinhosgrocery.utils.filename_utils import (
    FilenameData,
    generate_gdrive_filename,
)

logger = logging.getLogger(__name__)


class ReceiptProcessingService:
    def __init__(self, db_session: AsyncSession, bot_instance: Optional[Bot] = None):
        self.db_session = db_session
        self.bot = bot_instance

    async def _download_telegram_file(self, file_id: str) -> Optional[bytes]:
        """Downloads a file from Telegram given its file_id."""
        if not self.bot:
            logger.error(
                "Bot instance not available in ReceiptProcessingService to download file."
            )
            raise RuntimeError(
                "Bot instance not configured for Telegram file operations."
            )

        logger.info(
            f"Attempting to download Telegram file_id: {file_id} using provided bot instance."
        )
        try:
            file = await self.bot.get_file(file_id)
            file_bytes_bytearray = await file.download_as_bytearray()
            logger.info(
                f"Successfully downloaded file_id: {file_id}, size: {len(file_bytes_bytearray)} bytes."
            )
            return bytes(file_bytes_bytearray)
        except Exception as e:
            logger.exception(f"Error downloading Telegram file_id {file_id}: {e}")
            return None

    async def _perform_core_processing(
        self,
        file_content: bytes,
        original_input_filename: str,  # Renamed for clarity from effective_file_name
        user_telegram_id: Optional[
            int
        ] = None,  # Keep for consistency if needed in logging/future
    ) -> Receipt:
        """Core logic for processing receipt data after file content is obtained."""
        logger.info(f"Calling OpenAI API for file: {original_input_filename}")
        extracted_data = await extract_receipt_data_from_image(
            file_content, file_name=original_input_filename
        )

        if extracted_data.get("error"):
            error_message = f"OpenAI processing failed: {extracted_data.get('error')}"
            raw_response = extracted_data.get("raw_response")
            if raw_response:
                error_message += f" Raw Response: {raw_response[:500]}..."
            logger.error(error_message)
            raise ValueError(error_message)

        logger.info(
            f"OpenAI successfully extracted data for {original_input_filename}: {extracted_data}"
        )

        # ---- GDrive Filename Generation ----
        parsed_receipt_datetime: Optional[datetime.datetime] = None
        purchase_date_str = extracted_data.get("purchase_date")  # e.g., "YYYY-MM-DD"
        purchase_time_str = extracted_data.get(
            "purchase_time"
        )  # e.g., "HH:MM" or "HH:MM:SS"

        if purchase_date_str:
            try:
                date_part = datetime.datetime.strptime(
                    purchase_date_str, "%Y-%m-%d"
                ).date()
                time_part = datetime.time(
                    0, 0
                )  # Default time if not found or unparseable
                if purchase_time_str:
                    # Try parsing HH:MM:SS first, then HH:MM
                    for fmt in ("%H:%M:%S", "%H:%M"):
                        try:
                            time_part = datetime.datetime.strptime(
                                purchase_time_str.split(".")[0], fmt
                            ).time()
                            break  # Parsed successfully
                        except ValueError:
                            continue  # Try next format
                    else:  # If loop finished without break
                        logger.warning(
                            f"Could not parse purchase_time '{purchase_time_str}' with known formats. Using 00:00."
                        )
                parsed_receipt_datetime = datetime.datetime.combine(
                    date_part, time_part
                )
            except ValueError:
                logger.warning(
                    f"Could not parse purchase_date '{purchase_date_str}'. Fallback for timestamp will occur in filename util."
                )

        category_from_ocr = extracted_data.get("category", "grocery")
        store_name_from_ocr = extracted_data.get("store_name")
        _, original_extension = os.path.splitext(original_input_filename)

        filename_dto = FilenameData(
            receipt_datetime=parsed_receipt_datetime,
            category=category_from_ocr,
            store_name=store_name_from_ocr,
            original_extension=original_extension if original_extension else ".dat",
            original_filename_for_log=original_input_filename,
        )
        gdrive_filename_to_use = generate_gdrive_filename(filename_dto)
        logger.info(f"Generated Google Drive filename: {gdrive_filename_to_use}")
        # ---- End GDrive Filename Generation ----

        gdrive_id: Optional[str] = None
        gdrive_url: Optional[str] = None

        mime_type, _ = mimetypes.guess_type(
            original_input_filename
        )  # Mime type from original name for upload
        if not mime_type:
            # Basic fallback based on new filename's extension (which should match original)
            if gdrive_filename_to_use.lower().endswith((".jpg", ".jpeg")):
                mime_type = "image/jpeg"
            elif gdrive_filename_to_use.lower().endswith(".png"):
                mime_type = "image/png"
            elif gdrive_filename_to_use.lower().endswith(".pdf"):
                mime_type = "application/pdf"
            else:
                mime_type = "application/octet-stream"

        logger.info(
            f"Attempting to upload data from {original_input_filename} as {gdrive_filename_to_use} (MIME: {mime_type}) to Google Drive."
        )
        gdrive_upload_result = await upload_file_to_gdrive(
            file_bytes=file_content,
            file_name_on_drive=gdrive_filename_to_use,  # USE THE NEW FILENAME
            mime_type=mime_type,
        )

        if gdrive_upload_result and gdrive_upload_result.get("id"):
            gdrive_id = gdrive_upload_result.get("id")
            gdrive_url = gdrive_upload_result.get("webViewLink")
            logger.info(
                f"Successfully uploaded {gdrive_filename_to_use} to Google Drive: id={gdrive_id}, url={gdrive_url}"
            )
        else:
            logger.warning(
                f"Failed to upload {gdrive_filename_to_use} to Google Drive. Proceeding without GDrive links."
            )

        # Use parsed_receipt_datetime.date() if available, otherwise None for purchase_date_obj
        purchase_date_obj: Optional[datetime.date] = (
            parsed_receipt_datetime.date() if parsed_receipt_datetime else None
        )
        if (
            purchase_date_str and not purchase_date_obj
        ):  # Log if original string was there but parsing failed for date part
            logger.warning(
                f"Could not parse purchase_date '{purchase_date_str}' from OpenAI for DB. Storing as null."
            )

        db_receipt = Receipt(
            store_name=extracted_data.get(
                "store_name"
            ),  # Should we use normalized store_name_from_ocr here?
            purchase_date=purchase_date_obj,
            total_amount=extracted_data.get("total_amount"),
            gdrive_file_id=gdrive_id,
            gdrive_file_url=gdrive_url,
            gdrive_filename=gdrive_filename_to_use  # Added GDrive filename
            # user_telegram_id=user_telegram_id # Consider adding if you want to link receipts to users
        )
        self.db_session.add(db_receipt)
        await self.db_session.flush()

        items = extracted_data.get("items", [])
        if not isinstance(items, list):
            logger.warning(
                f"OpenAI returned 'items' not as a list for {original_input_filename}: {type(items)}. Defaulting to empty list."
            )
            items = []

        for item_data in items:
            if not isinstance(item_data, dict):
                logger.warning(
                    f"Skipping item_data as it's not a dictionary for {original_input_filename}: {item_data}"
                )
                continue

            # Extract tags, default to empty list if not found or not a list
            item_tags = item_data.get("tags", [])
            if not isinstance(item_tags, list):
                logger.warning(
                    f"Item tags for '{item_data.get('original_name')}' were not a list: {item_tags}. Defaulting to empty list."
                )
                item_tags = []

            db_product_entry = ProductEntry(
                receipt_id=db_receipt.id,
                receipt=db_receipt,
                original_name=item_data.get("original_name", "N/A"),
                generalized_name=item_data.get("generalized_name", "N/A"),
                price_per_unit=item_data.get("price_per_unit"),
                quantity=item_data.get("quantity", 1.0),
                weight_volume_text=item_data.get("weight_volume_text"),
                parsed_weight_grams=item_data.get("parsed_weight_grams"),
                parsed_volume_ml=item_data.get("parsed_volume_ml"),
                tags=item_tags,
            )
            self.db_session.add(db_product_entry)

        await self.db_session.refresh(db_receipt, attribute_names=["product_entries"])
        logger.info(
            f"Receipt and {len(db_receipt.product_entries)} product entries saved to DB for {gdrive_filename_to_use}, receipt_id: {db_receipt.id}"
        )
        return db_receipt

    async def process_new_receipt(
        self,
        telegram_file_id: str,
        original_file_name: Optional[str] = None,  # Made None default, will be derived
        user_telegram_id: Optional[int] = None,
    ) -> Receipt:
        """Processes a new receipt from Telegram."""
        if not self.bot:
            logger.error(
                "Cannot process new receipt from Telegram: Bot instance not provided."
            )
            raise RuntimeError("Bot instance is required for Telegram operations.")

        logger.info(
            f"Starting processing for Telegram receipt file_id: {telegram_file_id} from user {user_telegram_id}"
        )

        file_content = await self._download_telegram_file(telegram_file_id)
        if not file_content:
            logger.error(
                f"Failed to download file content from Telegram for file_id: {telegram_file_id}"
            )
            raise ValueError(
                f"Failed to download receipt file from Telegram (file_id: {telegram_file_id})."
            )

        # If original_file_name is not provided by Telegram message, construct a default one.
        # Telegram Bot API's File object has `file_path` which might contain a suggested filename by the client.
        # For now, if not provided, we'll use a generic name with file_id.
        effective_original_filename = original_file_name or f"{telegram_file_id}.dat"

        return await self._perform_core_processing(
            file_content, effective_original_filename, user_telegram_id
        )

    async def process_receipt_from_uploaded_file(
        self,
        file_content: bytes,
        original_file_name: str,
        user_identifier: Optional[str] = None,
    ) -> Receipt:
        """Processes a new receipt from directly uploaded file content."""
        logger.info(
            f"Starting processing for directly uploaded receipt file: {original_file_name} from user: {user_identifier}"
        )

        if not file_content:
            raise ValueError("No file content provided for direct upload.")
        if not original_file_name:
            raise ValueError("Original file name must be provided for direct upload.")

        # Passing user_identifier as None for user_telegram_id in _perform_core_processing
        # (as discussed, adapt if API user mapping to telegram ID or a generic user field in Receipt is needed)
        return await self._perform_core_processing(
            file_content, original_file_name, user_telegram_id=None
        )


# Example of how to get the service with a session (e.g. in a FastAPI dependency or handler)
# async def get_receipt_processing_service(
#     db: AsyncSession = Depends(get_async_db_session),
#     # bot: Bot = Depends(get_bot_instance) # If you have a way to inject bot globally
# ) -> ReceiptProcessingService:
#     # If bot is globally available through Depends(get_bot_instance)
#     # return ReceiptProcessingService(db_session=db, bot_instance=bot)
#     # Else, for API routes not needing bot, it can be instantiated with bot_instance=None
#     return ReceiptProcessingService(db_session=db) # Assuming API endpoint passes None for bot
