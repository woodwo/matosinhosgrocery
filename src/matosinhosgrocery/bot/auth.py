from telegram import Update

from matosinhosgrocery.config import settings


def is_user_allowed(update: Update) -> bool:
    """Checks if the user from the update is in the allowed list."""
    if not update.effective_user:
        return False
    if not settings.TELEGRAM_ALLOWED_USER_IDS: # If the list is empty, allow no one explicitly
        return False
    return update.effective_user.id in settings.TELEGRAM_ALLOWED_USER_IDS

async def unauthorized_reply(update: Update, context: "ContextTypes.DEFAULT_TYPE"):
    """Sends a standard reply to unauthorized users."""
    if update.message:
        await update.message.reply_text(
            "Sorry, you are not authorized to use this bot. "
            "Please deploy your own instance from the project repository if you wish to use this application."
        )
    elif update.callback_query:
        await update.callback_query.answer(
            "Sorry, you are not authorized for this action.", show_alert=True
        ) 