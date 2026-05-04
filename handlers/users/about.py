import logging
from aiogram.types import Message
from aiogram.filters import Command
from loader import dp

logger = logging.getLogger(__name__)


@dp.message(Command("about"))
async def about_commands(message: Message) -> None:
    """Bot haqida malumot"""
    about_text = (
        "ℹ️ <b>Bot haqida</b>\n\n"
        "Ushbu bot Muslim Team tomonidan yaratilgan.\n\n"
        "🔗 <b>Bizni kuzatib boring:</b>\n"
        "• Telegram: @muslim_team\n"
        "• Website: https://example.com\n\n"
        "📝 Bot versiyasi: 1.0.0"
    )
    await message.answer(about_text, parse_mode="HTML", disable_web_page_preview=True)
    logger.info(f"About requested by user {message.from_user.id}")

