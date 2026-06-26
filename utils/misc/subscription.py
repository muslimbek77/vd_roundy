import logging
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramAPIError

logger = logging.getLogger(__name__)


async def check(user_id: int, channel: int, bot: Bot) -> bool:
    """
    Foydalanuvchi kanalga obuna ekanligini tekshirish
    
    Args:
        user_id: Foydalanuvchining Telegram ID
        channel: Kanal ID (negative raqam, masalan: -1001234567890)
        bot: Bot instance
    
    Returns:
        bool: True agar obuna bo'lsa yoki xatolik bo'lsa, False agar obuna bo'lmasa
    """
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        is_member = member.status in ["member", "administrator", "creator"]
        
        if is_member:
            logger.debug(f"User {user_id} is subscribed to channel {channel}")
        
        return is_member

    except TelegramForbiddenError as e:
        logger.warning(f"Bot access denied for channel {channel}: {e}")
        try:
            from loader import db
            db.disable_channel(channel_id=channel)
        except Exception as db_error:
            logger.error(f"Failed to disable inaccessible channel {channel}: {db_error}")
        return True

    except TelegramBadRequest as e:
        logger.warning(f"Bad request for channel {channel}: {e}")
        error_text = str(e).lower()
        
        # Kanal yo'q yoki bot huquqi yo'q bo'lsa
        if any(text in error_text for text in ["not found", "no rights", "user not found"]):
            logger.info(f"Removing channel {channel} from database")
            try:
                from loader import db
                db.delete_channel(channel_id=channel)
            except Exception as db_error:
                logger.error(f"Failed to delete channel from DB: {db_error}")
            return False

        if any(
            text in error_text
            for text in [
                "chat_admin_required",
                "bot is not a member",
                "bot was kicked",
                "not enough rights",
                "forbidden",
            ]
        ):
            logger.warning(
                "Channel %s is not checkable right now, disabling it to avoid blocking users",
                channel,
            )
            try:
                from loader import db
                db.disable_channel(channel_id=channel)
            except Exception as db_error:
                logger.error(f"Failed to disable channel {channel}: {db_error}")
            return True

        return False

    except TelegramAPIError as e:
        logger.error(f"Telegram API error for channel {channel}: {e}")
        return False

    except Exception as e:
        logger.error(f"Unexpected error in subscription check: {e}", exc_info=True)
        return False
