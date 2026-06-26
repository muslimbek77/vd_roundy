import logging
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from typing import Callable, Dict, Any
from aiogram.types import ReplyKeyboardRemove
from aiogram.exceptions import TelegramAPIError
from keyboard_buttons.subscription import check_button
from utils.misc import subscription
from loader import ADMINS, db

logger = logging.getLogger(__name__)


class BigBrother(BaseMiddleware):
    """Kanal obunasini tekshirish middleware"""
    
    SKIP_COMMANDS = {"/start", "/help", "/about"}
    SKIP_CALLBACK = {"check_subs"}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Any],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Middleware ni chaqirish"""
        
        user_id = self._get_user_id(event)
        if user_id is None:
            return await handler(event, data)

        if db.is_banned(user_id):
            if isinstance(event, Message):
                await event.answer("⛔ Siz ushbu botdan foydalanishdan chetlatilgansiz.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Siz ushbu botdan foydalanishdan chetlatilgansiz.", show_alert=True)
            return
        
        # Tekshirish laridan o'tkazish kerak bo'ladigan holatlar
        if self._should_skip_check(event):
            return await handler(event, data)
        
        # Kanal obunasini tekshirish
        if not await self._check_subscriptions(event, data, user_id):
            return  # Handler chaqirilmaydi
        
        return await handler(event, data)
    
    @staticmethod
    def _get_user_id(event: TelegramObject) -> int | None:
        """Foydalanuvchi ID ni olib olish"""
        if isinstance(event, (Message, CallbackQuery)):
            return event.from_user.id
        return None
    
    @staticmethod
    def _should_skip_check(event: TelegramObject) -> bool:
        """Tekshiruvni o'tkazish kerakmi"""
        if isinstance(event, Message):
            text = (event.text or "").strip()
            return any(text.startswith(command) for command in BigBrother.SKIP_COMMANDS)
        elif isinstance(event, CallbackQuery):
            return event.data in BigBrother.SKIP_CALLBACK
        return False
    
    async def _check_subscriptions(
        self,
        event: TelegramObject,
        data: Dict[str, Any],
        user_id: int
    ) -> bool:
        """Kanal obunalarini tekshirish"""
        try:
            bot = data.get("bot")
            if not bot:
                logger.error("Bot not found in data")
                return False

            if user_id in ADMINS or db.is_admin(user_id):
                logger.debug("Skipping subscription check for admin %s", user_id)
                return True
            
            channels = db.select_all_channels(detailed=True, active_only=True)
            if not channels:
                logger.debug(f"No channels to check for user {user_id}")
                return True
            
            join_channel = []
            all_subscribed = True
            missing_channels_text = "Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:\n"
            extra_links_text = ""
            
            for channel_id, channel_name, channel_link, channel_mode, _, _, _ in channels:
                try:
                    if channel_mode == "external_link":
                        join_channel.append([channel_link, channel_name, 0])
                        extra_links_text += f"🤖 <a href='{channel_link}'>{channel_name}</a>\n"
                        continue

                    is_subscribed = False
                    if db.has_channel_join(channel_id, user_id):
                        is_subscribed = True
                    else:
                        is_subscribed = await subscription.check(
                            user_id=user_id,
                            channel=channel_id,
                            bot=bot
                        )
                    
                    if not is_subscribed:
                        all_subscribed = False
                        missing_channels_text += f"👉 <a href='{channel_link}'>{channel_name}</a>\n"
                    
                    join_channel.append([channel_link, channel_name, int(is_subscribed)])
                    
                except TelegramAPIError as e:
                    logger.error(f"Failed to check subscription for channel {channel_id}: {e}")
                    continue
            
            # Agar obuna bo'lmagan kanallar bo'lsa, habar yuborish
            if not all_subscribed:
                if extra_links_text:
                    missing_channels_text += "\nQo'shimcha havolalar:\n" + extra_links_text
                reply_markup = await check_button(join_channel)
                await self._send_subscription_message(event, missing_channels_text, reply_markup)
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in subscription check: {e}", exc_info=True)
            return True  # Xatolik bo'lsa, handlerni chaqirish
    
    @staticmethod
    async def _send_subscription_message(
        event: TelegramObject,
        message_text: str,
        reply_markup
    ) -> None:
        """Obuna habarini yuborish"""
        try:
            if isinstance(event, Message):
                await event.answer(
                    "Kanallarga to'liq obuna bo'ling",
                    reply_markup=ReplyKeyboardRemove()
                )
                await event.answer(
                    message_text,
                    disable_web_page_preview=True,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            elif isinstance(event, CallbackQuery):
                await event.message.answer(
                    "Kanallarga to'liq obuna bo'ling",
                    reply_markup=ReplyKeyboardRemove()
                )
                await event.message.answer(
                    message_text,
                    disable_web_page_preview=True,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
        except TelegramAPIError as e:
            logger.error(f"Failed to send subscription message: {e}")
