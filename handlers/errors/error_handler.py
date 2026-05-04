import logging
from aiogram import Dispatcher
from aiogram.types import Update
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)


async def error_handler(update: Update, exception: Exception) -> None:
    """
    Global xato qayta ishlash
    
    Args:
        update: Update object
        exception: Xato
    """
    logger.error(
        f"Update {update.update_id} caused error:\n{exception}",
        exc_info=True
    )
    
    # TelegramAPIError uchun maxsus qayta ishlash
    if isinstance(exception, TelegramAPIError):
        logger.error(f"Telegram API error: {exception}")


def setup_error_handlers(dp: Dispatcher) -> None:
    """Global xato handlerlarni o'rnatish"""
    dp.error_handler(error_handler)
    logger.info("Error handlers setup completed")