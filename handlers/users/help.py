import logging
from aiogram.types import Message
from aiogram.filters import Command
from loader import dp

logger = logging.getLogger(__name__)


@dp.message(Command("help"))
async def help_commands(message: Message) -> None:
    """Yordam komandasi"""
    help_text = (
        "🆘 <b>Yordam</b>\n\n"
        "Bot quyidagi xizmatlarni taqdim etadi:\n\n"
        "• 📢 Kanallar orqali habarlar olish\n"
        "• 🔔 Muhim yangiliklar haqida bildirishnoma\n"
        "• ⚙️ Shaxsiy sozlamalar\n\n"
        "Savollaringiz bo'lsa, admin bilan bog'laning."
    )
    await message.answer(help_text, parse_mode="HTML")
    logger.info(f"Help requested by user {message.from_user.id}")
