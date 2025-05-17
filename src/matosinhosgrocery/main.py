import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from matosinhosgrocery.bot.core import (
    initialize_telegram_bot_app,
    start_telegram_bot_polling,
    stop_telegram_bot_polling,
    global_bot_app,  # For type hinting or direct access if needed
)

# from matosinhosgrocery.database.connection import create_db_and_tables # Import the function
from matosinhosgrocery.config import settings # Import settings for logging

# UPDATED: Import receipt_routes directly from matosinhosgrocery package
from matosinhosgrocery import receipt_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.APP_NAME}...")

    # Initialize and start the Telegram bot
    # await create_db_and_tables()
    initialize_telegram_bot_app() # This sets bot.core.global_bot_app
    
    # The start_telegram_bot_polling function itself will check if global_bot_app was successfully initialized.
    logger.info("Attempting to create polling task (start_telegram_bot_polling will check if bot is initialized)...")
    polling_task = asyncio.create_task(start_telegram_bot_polling())
    # Giving the task a name can be helpful for debugging asyncio tasks
    # In Python 3.8+ tasks are named automatically if not specified. For older, can do: polling_task.set_name("TelegramPollingTask")
    logger.info(f"Polling task created: {polling_task.get_name() if hasattr(polling_task, 'get_name') else 'N/A'}. Waiting for it to start logging...")

    yield
    # Shutdown
    logger.info(f"Ctrl+C received. Shutting down {settings.APP_NAME} gracefully...")
    
    # The stop_telegram_bot_polling function will also check global_bot_app
    # No need to check global_bot_app directly in main.py for shutdown either.
    await stop_telegram_bot_polling() 
    # Previous shutdown logic for global_bot_app.updater and global_bot_app.stop() etc. 
    # is now encapsulated within stop_telegram_bot_polling().
    
    # if global_bot_app and global_bot_app.updater:
    #     if global_bot_app.updater.running:
    #         logger.info("Attempting to stop Telegram bot updater...")
    #         await global_bot_app.updater.stop()
    #         logger.info("Telegram bot updater stopped.")
    #     else:
    #         logger.info("Telegram bot updater was not running.")
            
    #     logger.info("Attempting to stop Telegram bot application tasks (e.g., job_queue)...")
    #     await global_bot_app.stop() # Stops the Application's internal tasks (like JobQueue)
    #     logger.info("Telegram bot application tasks stopped.")
        
    #     logger.info("Attempting to shutdown Telegram bot application (final cleanup)...")
    #     await global_bot_app.shutdown() # Performs final cleanup
    #     logger.info("Telegram bot application shutdown complete.")
    # else:
    #     logger.info("Telegram bot application was not initialized or updater not present during shutdown.")

    logger.info(f"{settings.APP_NAME} shutdown process finished.")

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="A Telegram bot to help manage your grocery receipts and lists in Matosinhos.",
    lifespan=lifespan
)

# NEW: Include the receipt_api_router
app.include_router(receipt_routes.receipt_api_router, prefix="/api/v1", tags=["Receipts"])

@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "bot_initialized": global_bot_app is not None}

# Further application setup (like DB connections) will be added here or in dedicated modules. 