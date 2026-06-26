import logging
from typing import List
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, TelegramObject
from loader import db

logger = logging.getLogger(__name__)


class IsBotAdminFilter(BaseFilter):
    """Admin roli tekshiruvchi filter"""
    
    def __init__(self, user_ids: List[int]):
        self.user_ids = set(user_ids)  # Set uchun tezroq qidirish

    async def __call__(self, event: TelegramObject) -> bool:
        """Foydalanuvchi admin ekanligini tekshirish"""
        from_user = getattr(event, "from_user", None)
        if from_user is None:
            return False

        is_admin = from_user.id in self.user_ids or db.is_admin(from_user.id)
        
        if not is_admin:
            logger.warning("Unauthorized admin access attempt by user %s", from_user.id)
        
        return is_admin


class IsSuperAdminFilter(BaseFilter):
    """Faqat .env dagi super adminlar uchun filter"""

    def __init__(self, user_ids: List[int]):
        self.user_ids = set(user_ids)

    async def __call__(self, event: TelegramObject) -> bool:
        from_user = getattr(event, "from_user", None)
        if from_user is None:
            return False

        is_super_admin = from_user.id in self.user_ids
        if not is_super_admin:
            logger.warning("Unauthorized super-admin access attempt by user %s", from_user.id)
        return is_super_admin
