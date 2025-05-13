import logging
import asyncio
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters, Application

from matosinhosgrocery.bot.auth import is_user_allowed, unauthorized_reply
from matosinhosgrocery.database.connection import AsyncSessionLocal # Import session factory
from matosinhosgrocery.services.receipt_processing_service import ReceiptProcessingService

logger = logging.getLogger(__name__)

async def process_receipt_task(
    context: ContextTypes.DEFAULT_TYPE,
    telegram_file_id: str,
    original_file_name: str,
    user_telegram_id: int,
    chat_id: int
):
    """Runs the receipt processing in the background and notifies the user."""
    session: Optional[AsyncSession] = None # For logging in finally block
    try:
        logger.info("[DB_SESSION_DEBUG] process_receipt_task: Attempting to acquire DB session.")
        async with AsyncSessionLocal() as session:
            logger.info(f"[DB_SESSION_DEBUG] process_receipt_task: DB Session acquired: {session}, active: {session.is_active}")
            service = ReceiptProcessingService(db_session=session, bot_instance=context.bot)
            receipt = await service.process_new_receipt(
                telegram_file_id=telegram_file_id,
                original_file_name=original_file_name,
                user_telegram_id=user_telegram_id
            )
            # Explicit commit here before trying to send message, to be absolutely sure
            # though the context manager should handle it.
            logger.info(f"[DB_SESSION_DEBUG] process_receipt_task: Processing complete, attempting explicit commit. Session active: {session.is_active}")
            await session.commit()
            logger.info(f"[DB_SESSION_DEBUG] process_receipt_task: Explicit commit successful. Session active: {session.is_active}")
            
        # session should be committed and closed by context manager exiting here if no error before explicit commit
        logger.info(f"[DB_SESSION_DEBUG] process_receipt_task: Exited AsyncSessionLocal context. Receipt ID: {receipt.id if receipt else 'N/A'}")

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Successfully processed receipt from {receipt.store_name} (ID: {receipt.id}) with {len(receipt.product_entries)} items!"
        )
        logger.info(f"[DB_SESSION_DEBUG] process_receipt_task: Successfully sent confirmation message to user for receipt {receipt.id}")

    except ValueError as ve:
        logger.error(f"[DB_SESSION_DEBUG] process_receipt_task: ValueError: {ve}. Session state before potential rollback: {session.is_active if session else 'N/A'}")
        # Rollback should happen in __aexit__ of AsyncSessionLocal if an error propagates
        await context.bot.send_message(chat_id=chat_id, text=f"Error processing receipt: {ve}")
    except Exception as e:
        logger.exception(f"[DB_SESSION_DEBUG] process_receipt_task: Unexpected Exception: {e}. Session state before potential rollback: {session.is_active if session else 'N/A'}")
        # Rollback should happen in __aexit__ of AsyncSessionLocal
        import traceback
        tb_str = traceback.format_exc()
        error_message = f"An unexpected error occurred. Please show this to the admin:\n<pre>{tb_str[:4000]}</pre>"
        await context.bot.send_message(chat_id=chat_id, text=error_message, parse_mode="HTML")
    finally:
        # This block is just for logging the final state if needed, actual close is handled by context manager
        if session:
            # Note: session.is_active might be False here if commit/rollback + close already happened
            logger.info(f"[DB_SESSION_DEBUG] process_receipt_task: In finally block. Session active: {session.is_active}, dirty: {session.dirty}, new: {len(session.new)}")
        else:
            logger.info("[DB_SESSION_DEBUG] process_receipt_task: In finally block. Session was None (likely error before acquisition).")


async def handle_receipt_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming documents (potential receipts)."""
    if not is_user_allowed(update):
        await unauthorized_reply(update, context)
        return

    user = update.effective_user
    message = update.message
    
    file_id = None
    original_file_name = "receipt_file"

    if message.document:
        document = message.document
        file_id = document.file_id
        original_file_name = document.file_name
        logger.info(f"User {user.id} sent document: {original_file_name} (ID: {file_id}).")
        await message.reply_text(f"Got your document: {original_file_name}. Processing it now...")
    
    elif message.photo:
        photo_size = message.photo[-1]
        file_id = photo_size.file_id
        original_file_name = f"photo_{file_id}.jpg" # Create a generic name for photos
        logger.info(f"User {user.id} sent photo (ID: {file_id}).")
        await message.reply_text("Got your photo! Processing it now...")
    
    else:
        logger.warning(f"Receipt handler triggered for unexpected message type from user {user.id}")
        await message.reply_text("I'm not sure what to do with that as a receipt.")
        return

    # Schedule the processing in the background
    # context.application.create_task is preferred if available and correctly configured with the event loop.
    # For PTB v20+, Application ensures tasks run on its loop.
    # If context.application is not the main FastAPI app's Application instance from bot.core,
    # ensure tasks are created on the correct loop or use asyncio.create_task directly.
    
    # Using asyncio.create_task directly for simplicity here, assuming the handler runs on the main event loop.
    asyncio.create_task(
        process_receipt_task(
            context=context,
            telegram_file_id=file_id,
            original_file_name=original_file_name,
            user_telegram_id=user.id,
            chat_id=message.chat_id
        )
    )

# Define a filter for messages that are photos or specific document types (PDF, common image types)
# This provides more specific filtering than just `filters.Document.ALL`
receipt_filters = (
    filters.PHOTO |
    filters.Document.PDF |
    filters.Document.IMAGE # Covers common image mimetypes like image/jpeg, image/png when sent as document
)

receipt_message_handler = MessageHandler(receipt_filters, handle_receipt_document) 