import logging
from typing import List, Tuple
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.exceptions import TelegramAPIError
from loader import bot

logger = logging.getLogger(__name__)


async def check_button(channels: List[Tuple]) -> InlineKeyboardMarkup:
    """
    Obuna tekshirish tugmalari uchun inline keyboard yaratish
    
    Args:
        channels: Kanallar ro'yxati [(link, name, subscribed), ...]
    
    Returns:
        InlineKeyboardMarkup: Inline keyboard markup
    """
    try:
        buttons = []
        
        for channel_link, channel_name, is_subscribed in channels:
            # Obuna status bo'yicha emoji qo'shish
            status_emoji = "✅" if is_subscribed else "👉"
            
            button = InlineKeyboardButton(
                text=f"{status_emoji} {channel_name}",
                url=channel_link
            )
            buttons.append([button])
        
        # Obunani tekshirish tugmasi
        check_button_obj = InlineKeyboardButton(
            text="🔄 Obunani qayta tekshirish",
            callback_data="check_subs"
        )
        buttons.append([check_button_obj])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        logger.debug(f"Subscription keyboard created with {len(buttons)} buttons")
        
        return keyboard
        
    except Exception as e:
        logger.error(f"Error creating subscription keyboard: {e}")
        # Fallback keyboard
        fallback = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="🔄 Obunani qayta tekshirish",
                    callback_data="check_subs"
                )
            ]]
        )
        return fallback