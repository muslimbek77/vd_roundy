import time
import logging
from typing import Callable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import Message

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """Foydalanuvchilarning so'rovlarini boshqarish middleware"""
    
    def __init__(self, slow_mode_delay: float = 0.5):
        self.user_timeouts: Dict[int, float] = {}
        self.slow_mode_delay = slow_mode_delay
        super().__init__()

    async def __call__(
        self, 
        handler: Callable, 
        event: Message, 
        data: Dict[str, Any]
    ) -> Any:
        """Middleware ni chaqirish"""
        user_id = event.from_user.id
        current_time = time.time()
        
        last_request_time = self.user_timeouts.get(user_id, 0)
        time_diff = current_time - last_request_time
        
        # So'rovlar oralig'ini tekshirish
        if 0 < time_diff < self.slow_mode_delay:
            logger.warning(f"User {user_id} exceeded rate limit")
            await event.reply(
                "⏱️ Juda ko'p so'rov! Iltimos, {:.1f} soniya kuting.".format(
                    self.slow_mode_delay - time_diff
                )
            )
            return
        
        # Oxirgi so'rovning vaqtini yangilash
        self.user_timeouts[user_id] = current_time
        
        # Handler ni chaqirish
        return await handler(event, data)