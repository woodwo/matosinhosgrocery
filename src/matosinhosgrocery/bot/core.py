import logging
from typing import Optional  # Added for type hinting

from telegram.ext import Application

from matosinhosgrocery.config import settings

logger = logging.getLogger(__name__)

# Global bot application instance, to be initialized by initialize_telegram_bot_app
global_bot_app: Optional[Application] = None


async def post_init(application: Application) -> None:
    """Post initialization hook for the bot application."""
    logger.info(
        f"Bot {application.bot.username} (ID: {application.bot.id}) started and post_init executed."
    )
    # Example: Set bot commands
    # await application.bot.set_my_commands([
    #     ("new_receipt", "Upload a new receipt image/document"),
    #     ("help", "Show help message")
    # ])
    # logger.info("Bot commands have been set.")


def initialize_telegram_bot_app() -> None:
    """Initializes the global Telegram bot application and its handlers."""
    global global_bot_app  # Declare intent to modify the global variable

    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN is not set. Bot application cannot be initialized."
        )
        # No need to raise here, main.py will log and proceed without bot functionality if token is missing.
        # The global_bot_app will remain None.
        return

    try:
        application = (
            Application.builder()
            .token(settings.TELEGRAM_BOT_TOKEN)
            .post_init(post_init)
            # .read_timeout(30)  # Optional: for operations like get_file
            # .get_updates_read_timeout(30) # Optional: for get_updates polling
            .build()
        )

        # Import and register handlers
        from .handlers import receipts  # Import the receipts handlers module

        application.add_handler(receipts.receipt_message_handler)
        logger.info("Receipt message handler registered.")

        # Add other handlers here if needed (e.g., command handlers)
        # from .handlers import general
        # application.add_handler(general.start_handler)
        # logger.info("General command handlers registered.")

        global_bot_app = application
        logger.info("Telegram bot application initialized successfully.")

    except Exception as e:
        logger.exception("Failed to initialize Telegram bot application.")
        global_bot_app = None  # Ensure it's None on failure


async def start_telegram_bot_polling() -> None:
    """Starts the Telegram bot's polling mechanism."""
    logger.info(
        "Attempting to start Telegram bot polling process..."
    )  # Log entry to the function
    if global_bot_app:
        logger.info(
            f"global_bot_app found. Updater: {global_bot_app.updater}, Updater running: {global_bot_app.updater.running if global_bot_app.updater else 'N/A'}"
        )
        # The condition `not global_bot_app.updater` might be too strict if PTB sets it up during initialize()
        # Let's rely on initialize() to set up the updater if not present.
        if not global_bot_app.updater or not global_bot_app.updater.running:
            logger.info(
                "Updater not present or not running. Proceeding to initialize and start polling."
            )
            try:
                logger.info("Calling global_bot_app.initialize()...")
                await global_bot_app.initialize()  # Initializes handlers, job queue etc.
                logger.info("global_bot_app.initialize() completed.")

                if global_bot_app.updater:
                    logger.info(
                        "Updater found after initialize. Calling updater.start_polling()..."
                    )
                    await global_bot_app.updater.start_polling(
                        drop_pending_updates=True
                    )
                    logger.info("updater.start_polling() completed.")
                else:
                    logger.error(
                        "Updater still not available after global_bot_app.initialize(). Polling cannot start."
                    )
                    return  # Exit if no updater

                logger.info("Calling global_bot_app.start()...")
                await global_bot_app.start()  # Starts other internal tasks (e.g. job queue)
                logger.info(
                    "global_bot_app.start() completed. Telegram bot polling should now be active."
                )
            except Exception as e:
                logger.exception("Error during Telegram bot polling startup sequence.")
        else:
            logger.info(
                "Telegram bot polling is already running or updater indicates it is."
            )
    else:
        logger.warning(
            "Telegram bot application not initialized. Polling cannot start."
        )


async def stop_telegram_bot_polling() -> None:
    """Stops the Telegram bot's polling and shuts down the application gracefully."""
    if global_bot_app:
        logger.info("Attempting to stop Telegram bot...")
        try:
            if global_bot_app.updater and global_bot_app.updater.running:
                logger.info("Stopping bot updater polling...")
                await global_bot_app.updater.stop()
                logger.info("Bot updater polling stopped.")
            else:
                logger.info("Bot updater was not running or not available.")

            if global_bot_app.running:  # Check if application itself is running tasks
                logger.info(
                    "Stopping bot application (internal tasks like job queue)..."
                )
                await global_bot_app.stop()
                logger.info("Bot application internal tasks stopped.")
            else:
                logger.info("Bot application internal tasks were not running.")

            logger.info("Shutting down bot application (final cleanup)...")
            await global_bot_app.shutdown()
            logger.info("Bot application shutdown complete.")
        except Exception as e:
            logger.exception("Error during Telegram bot stop/shutdown sequence.")
    else:
        logger.info(
            "Telegram bot application was not initialized. No stop action needed."
        )


# Removed old bot_app and create_bot_app function
