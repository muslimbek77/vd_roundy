import logging
from aiogram import Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart
from loader import dp, db, ADMINS

logger = logging.getLogger(__name__)


@dp.message(CommandStart())
async def start_command(message: Message) -> None:
    """Botni start qilish komandasi"""
    full_name = message.from_user.full_name or "Unknown"
    telegram_id = message.from_user.id
    
    try:
        db.add_user(full_name=full_name, telegram_id=telegram_id)
        logger.info(f"New user added: {telegram_id} - {full_name}")
        await message.answer(
            text="👋 Assalomu alaykum, botimizga hush kelibsiz!\n\n"
                 "Men sizga yordam berish uchun tayyorman."
        )
    except Exception as e:
        logger.warning(f"User {telegram_id} already exists or error occurred: {e}")
        await message.answer(
            text="👋 Assalomu alaykum! Qayta hush kelibsiz."
        )

