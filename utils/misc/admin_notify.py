import logging
from html import escape

from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from loader import ADMINS, bot, db
from keyboard_buttons.admin_keyboard import video_admin_actions

logger = logging.getLogger(__name__)


def build_user_link(user_id: int, full_name: str) -> str:
    safe_name = escape(full_name or "Foydalanuvchi")
    return f"<a href='tg://user?id={user_id}'>{safe_name}</a>"


async def send_admin_message(text: str) -> None:
    admin_ids = db.list_admin_ids() or ADMINS
    for admin_id in admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=text)
        except TelegramAPIError as error:
            logger.warning("Failed to send admin message to %s: %s", admin_id, error)
        except Exception as error:
            logger.exception("Unexpected admin notification error for %s: %s", admin_id, error)


async def notify_new_user(user_id: int, full_name: str) -> None:
    await send_admin_message(
        "🆕 Botga yangi foydalanuvchi qo'shildi.\n\n"
        f"👤 Ism-familya: {escape(full_name or 'Nomaʼlum')}\n"
        f"🔗 Profil: {build_user_link(user_id, full_name)}\n"
        f"🆔 ID: <code>{user_id}</code>"
    )


async def notify_video_submission(message: Message, conversion_type: str) -> None:
    full_name = message.from_user.full_name or "Nomaʼlum"
    text = (
        "🎬 Yangi video qayta ishlash so'rovi.\n\n"
        f"👤 Foydalanuvchi: {escape(full_name)}\n"
        f"🔗 Profil: {build_user_link(message.from_user.id, full_name)}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"🔄 Amal: {escape(conversion_type)}"
    )

    admin_ids = db.list_admin_ids() or ADMINS
    for admin_id in admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=text)
            await bot.copy_message(
                chat_id=admin_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                reply_markup=video_admin_actions(message.from_user.id),
            )
        except TelegramAPIError as error:
            logger.warning("Failed to deliver media audit to admin %s: %s", admin_id, error)
        except Exception as error:
            logger.exception("Unexpected video audit error for admin %s: %s", admin_id, error)
