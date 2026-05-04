import logging
from typing import List

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from data import config
from baza.sqlite import Database

logger = logging.getLogger(__name__)

# Konfiguratsiyani olib olish
ADMINS: List[int] = config.ADMINS
TOKEN: str = config.BOT_TOKEN

# Bot va Dispatcher ini yaratish
try:
    bot = Bot(
        TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    logger.info("Bot initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize bot: {e}")
    raise

# Database ni yaratish
try:
    db = Database(path_to_db="main.db", debug=False)
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    raise

# Dispatcher ni yaratish
dp = Dispatcher()