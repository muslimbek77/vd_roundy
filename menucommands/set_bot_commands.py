import logging
from typing import List
from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)


async def set_default_commands(bot: Bot) -> None:
    """
    Bot komandalarini o'rnatish
    
    Args:
        bot: Bot instance
    """
    commands: List[BotCommand] = [
        BotCommand(command="start", description="🚀 Botni ishga tushirish"),
        BotCommand(command="help", description="🆘 Yordam olish"),
        BotCommand(command="about", description="ℹ️ Bot haqida ma'lumot"),
    ]
    
    try:
        await bot.set_my_commands(
            commands=commands,
            scope=BotCommandScopeAllPrivateChats()
        )
        logger.info(f"Bot commands set successfully: {len(commands)} commands")
    except TelegramAPIError as e:
        logger.error(f"Failed to set bot commands: {e}")
    except Exception as e:
        logger.error(f"Unexpected error setting bot commands: {e}", exc_info=True)