import logging
from aiogram import F
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message
from aiogram.filters import CommandStart
from keyboard_buttons.subscription import check_button
from loader import ADMINS, bot, dp, db
from utils.misc import subscription
from utils.misc.admin_notify import notify_new_user

logger = logging.getLogger(__name__)


@dp.message(CommandStart())
async def start_command(message: Message) -> None:
    """Botni start qilish komandasi"""
    full_name = message.from_user.full_name or "Unknown"
    telegram_id = message.from_user.id
    
    try:
        created = db.add_user(full_name=full_name, telegram_id=telegram_id)
        db.touch_user(telegram_id=telegram_id, full_name=full_name)
        if created:
            logger.info(f"New user added: {telegram_id} - {full_name}")
            if telegram_id not in set(ADMINS):
                await notify_new_user(user_id=telegram_id, full_name=full_name)
            await message.answer(
                text=(
                    "👋 Assalomu alaykum!\n\n"
                    "Menga oddiy to'rtburchak video yuborsangiz, uni Telegram yumaloq "
                    "video formatiga o'tkazib beraman.\n"
                    "Agar yumaloq video yuborsangiz, uni oddiy MP4 video qilib qaytaraman.\n\n"
                    "Ishni boshlash uchun video yoki yumaloq video yuboring."
                )
            )
            return

        await message.answer(
            text=(
                "👋 Qayta hush kelibsiz!\n\n"
                "Video yuboring, men uni kerakli formatga o'tkazib beraman."
            )
        )
    except Exception as e:
        logger.error(f"Start command failed for {telegram_id}: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")


@dp.callback_query(F.data == "check_subs")
async def recheck_subscriptions(call: CallbackQuery) -> None:
    user_id = call.from_user.id
    channels = db.select_all_channels(detailed=True, active_only=True)

    if not channels:
        await call.answer("✅ Majburiy kanallar mavjud emas.", show_alert=True)
        return

    join_channel = []
    missing_channels_text = "Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:\n"
    all_subscribed = True
    extra_links_text = ""

    for channel_id, channel_name, channel_link, channel_mode, _, _, _ in channels:
        if channel_mode == "external_link":
            join_channel.append([channel_link, channel_name, 0])
            extra_links_text += f"🤖 <a href='{channel_link}'>{channel_name}</a>\n"
            continue

        try:
            is_subscribed = db.has_channel_join(channel_id, user_id) or await subscription.check(
                user_id=user_id,
                channel=channel_id,
                bot=bot,
            )
        except TelegramAPIError as error:
            logger.error("Failed to recheck subscription for %s: %s", channel_id, error)
            is_subscribed = False

        if not is_subscribed:
            all_subscribed = False
            missing_channels_text += f"👉 <a href='{channel_link}'>{channel_name}</a>\n"

        join_channel.append([channel_link, channel_name, int(is_subscribed)])

    if all_subscribed:
        await call.answer("✅ Obuna tasdiqlandi. Endi botdan foydalanishingiz mumkin.", show_alert=True)
        try:
            await call.message.delete()
        except TelegramAPIError:
            pass
        return

    if extra_links_text:
        missing_channels_text += "\nQo'shimcha havolalar:\n" + extra_links_text

    await call.answer("❌ Hali barcha kanallarga obuna bo'lmagansiz.", show_alert=True)
    await call.message.edit_text(
        missing_channels_text,
        disable_web_page_preview=True,
        reply_markup=await check_button(join_channel),
        parse_mode="HTML",
    )
