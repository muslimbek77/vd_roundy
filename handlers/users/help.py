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
        "• Oddiy video yuboring, bot uni yumaloq video qilib beradi.\n"
        "• Yumaloq video yuboring, bot uni oddiy MP4 video qilib beradi.\n"
        "• Fayl qayta ishlanayotganda biroz kuting, bot tayyor bo'lgach natijani yuboradi.\n\n"
        "Agar Telegram audio yoki video message qabul qilishni cheklagan bo'lsa, "
        "bot sizga uni yoqib qayta urinib ko'rishni aytadi."
    )
    await message.answer(help_text, parse_mode="HTML")
    logger.info(f"Help requested by user {message.from_user.id}")
