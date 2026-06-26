import logging
from typing import List, Sequence, Tuple
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButtonRequestChat
)

logger = logging.getLogger(__name__)

def admin_menu(is_super_admin: bool) -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="📊 Statistika"),
            KeyboardButton(text="📤 Xabar tarqatish"),
        ],
        [
            KeyboardButton(text="🔖 Kanallar ro'yxati"),
            KeyboardButton(text="🛡 Adminlar ro'yxati"),
        ],
        [
            KeyboardButton(text="➕ Kanal qo'shish"),
            KeyboardButton(text="🎯 Zayafkali kanal qo'shish"),
        ],
        [
            KeyboardButton(text="➖ Kanal o'chirish"),
        ],
    ]

    if is_super_admin:
        keyboard.append(
            [
                KeyboardButton(text="👤 Yangi admin qo'shish"),
                KeyboardButton(text="🚫 Adminlikdan olish"),
            ]
        )

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="📋 Menudan birini tanlang",
    )


def inline_wars_btn(channels: List[Tuple]) -> InlineKeyboardMarkup:
    """
    Kanallarni tanlash uchun inline buttons yaratish
    
    Args:
        channels: Kanallar ro'yxati
    
    Returns:
        InlineKeyboardMarkup: Inline keyboard markup
    """
    if not channels:
        logger.warning("No channels provided for inline buttons")
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="↩️ Orqaga", callback_data="back_admin")
        ]])
    
    # Tugmalar soniga ko'ra qatorni aniqlash
    button_count = len(channels)
    buttons_per_row = 3 if button_count <= 6 else 4 if button_count <= 8 else 6
    
    # Tugmalarni yaratish
    buttons = []
    for idx, channel in enumerate(channels, 1):
        channel_id = channel[0]
        buttons.append(InlineKeyboardButton(
            text=f"#{idx}",
            callback_data=str(channel_id)
        ))
    
    # Qatorlarga bo'lish
    keyboard = []
    for i in range(0, len(buttons), buttons_per_row):
        keyboard.append(buttons[i:i + buttons_per_row])
    
    # Orqaga tugmasi
    keyboard.append([
        InlineKeyboardButton(text="↩️ Orqaga", callback_data="back_admin")
    ])
    
    logger.debug(f"Created inline keyboard with {len(buttons)} channels")
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def channel_add_options() -> InlineKeyboardMarkup:
    """Kanal qo'shish usullarini tanlash tugmalari"""
    buttons = [
        [InlineKeyboardButton(text="📌 Postni forward qilish", callback_data="add_forward")],
        [InlineKeyboardButton(text="🔢 ID yuborish (-100...)", callback_data="add_id")],
        [InlineKeyboardButton(text="📝 Username yuborish (@kanal)", callback_data="add_username")],
        [InlineKeyboardButton(text="🔗 Link yuborish", callback_data="add_link")],
    ]
    logger.debug("Channel add options keyboard created")
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def channel_request_keyboard() -> ReplyKeyboardMarkup:
    """Kanal yoki guruhni Telegram tanlash oynasi orqali yuborish"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📢 Mening kanalni tanlash",
                    request_chat=KeyboardButtonRequestChat(
                        request_id=101,
                        chat_is_channel=True,
                        request_title=True,
                        request_username=True,
                    ),
                )
            ],
            [
                KeyboardButton(
                    text="👥 Mening guruhni tanlash",
                    request_chat=KeyboardButtonRequestChat(
                        request_id=102,
                        chat_is_channel=False,
                        request_title=True,
                        request_username=True,
                    ),
                )
            ],
            [KeyboardButton(text="🔢 ID yuborish"), KeyboardButton(text="📝 Username yuborish")],
            [KeyboardButton(text="🔗 Link yuborish")],
            [KeyboardButton(text="↩️ Admin menyuga qaytish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Kanal yoki guruhni tanlang",
    )


def support_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🚫 Bekor qilish")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def optional_link_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔗 Link yuborish")],
            [KeyboardButton(text="⏭ O'tkazib yuborish")],
            [KeyboardButton(text="🚫 Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def removable_admins_keyboard(admins: Sequence[Tuple[int, str]]) -> InlineKeyboardMarkup:
    buttons = []
    for admin_id, full_name in admins:
        display_name = full_name or str(admin_id)
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🚫 {display_name[:40]}",
                    callback_data=f"admin_remove:{admin_id}",
                )
            ]
        )

    buttons.append([InlineKeyboardButton(text="↩️ Yopish", callback_data="admins_close")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def video_admin_actions(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⛔ Ban berish", callback_data=f"video_ban:{user_id}"),
                InlineKeyboardButton(text="📢 Xabar yuborish", callback_data=f"video_notify:{user_id}"),
            ],
            [
                InlineKeyboardButton(text="❔ So'rash", callback_data=f"video_ask:{user_id}"),
            ],
        ]
    )
