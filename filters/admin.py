import logging
from typing import List
from aiogram.filters import BaseFilter
from aiogram.types import Message

logger = logging.getLogger(__name__)


class IsBotAdminFilter(BaseFilter):
    """Admin roli tekshiruvchi filter"""
    
    def __init__(self, user_ids: List[int]):
        self.user_ids = set(user_ids)  # Set uchun tezroq qidirish

    async def __call__(self, message: Message) -> bool:
        """Foydalanuvchi admin ekanligini tekshirish"""
        is_admin = message.from_user.id in self.user_ids
        
        if not is_admin:
            logger.warning(f"Unauthorized admin access attempt by user {message.from_user.id}")
        
        return is_admin

