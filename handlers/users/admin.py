import asyncio
import logging
from datetime import datetime
from time import time_ns
from urllib.parse import parse_qs, urlparse

from aiogram import F
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from filters.admin import IsBotAdminFilter, IsSuperAdminFilter
from keyboard_buttons import admin_keyboard
from loader import ADMINS, bot, db, dp
from states.reklama import AdminState, Adverts, ChannelState, DelChannelState, SupportState

logger = logging.getLogger(__name__)

ADVERT_DELAY = 0.01


def _is_super_admin(user_id: int) -> bool:
    return user_id in set(ADMINS)


def _admin_menu_markup(user_id: int):
    return admin_keyboard.admin_menu(is_super_admin=_is_super_admin(user_id))


@dp.message(Command("admin"), IsBotAdminFilter(ADMINS))
async def is_admin(message: Message) -> None:
    logger.info("Admin menu requested by %s", message.from_user.id)
    await message.answer(
        text="🔐 Admin menyu",
        reply_markup=_admin_menu_markup(message.from_user.id),
    )


@dp.message(F.text.in_({"Foydalanuvchilar soni", "Bot statistikasi", "📊 Statistika"}), IsBotAdminFilter(ADMINS))
async def users_count(message: Message) -> None:
    try:
        total_users = db.count_users()
        active_users = db.count_active_users()
        inactive_users = db.count_inactive_users()
        bot_created_at = _format_bot_created_at(db.get_meta("bot_created_at"))
        admins_count = db.count_admins()
        text = (
            "📊 <b>Bot statistikasi</b>\n\n"
            f"📅 Bot yaratilgan sana: <b>{bot_created_at}</b>\n"
            f"👥 Foydalanuvchilar soni: <b>{total_users}</b>\n"
            f"🟢 Faol: <b>{active_users}</b>\n"
            f"🔴 Nofaol: <b>{inactive_users}</b>\n"
            f"🛡 Adminlar soni: <b>{admins_count}</b>"
        )
        await message.answer(text=text, parse_mode="HTML")
    except Exception as error:
        logger.error("Failed to get bot stats: %s", error)
        await message.answer("❌ Xato: Bot statistikasini olib bo'lmadi")


@dp.message(F.text.in_({"Reklama yuborish", "📤 Xabar tarqatish"}), IsBotAdminFilter(ADMINS))
async def advert_dp(message: Message, state: FSMContext) -> None:
    await state.set_state(Adverts.adverts)
    logger.info("Advert mode started by admin %s", message.from_user.id)
    await message.answer(
        text="📢 Reklama yuborishingiz mumkin!\n\n"
        "Iltimos, reklama mazmunini yuboring (matn, rasm, video yoki fayl):"
    )


@dp.message(Adverts.adverts, IsBotAdminFilter(ADMINS))
async def send_advert(message: Message, state: FSMContext) -> None:
    users = db.all_users_id()
    if not users:
        await message.answer("⚠️ Foydalanuvchilar mavjud emas")
        await state.clear()
        return

    status_msg = await message.answer("⏳ Xabar tarqatilmoqda...")
    count = 0
    failed = 0

    try:
        for user in users:
            try:
                await bot.copy_message(
                    chat_id=user[0],
                    from_chat_id=message.from_user.id,
                    message_id=message.message_id,
                )
                db.set_user_active(user[0], True)
                count += 1
            except TelegramAPIError as error:
                logger.warning("Failed to send advert to user %s: %s", user[0], error)
                db.set_user_active(user[0], False)
                failed += 1
            except Exception as error:
                logger.error("Unexpected advert error for user %s: %s", user[0], error)
                failed += 1

            await asyncio.sleep(ADVERT_DELAY)

        await status_msg.edit_text(
            "📊 Xabar tarqatish tugadi!\n\n"
            f"✅ Yuborildi: <b>{count}</b>\n"
            f"❌ Xato: <b>{failed}</b>",
            parse_mode="HTML",
        )
    except Exception as error:
        logger.error("Error during advert send: %s", error)
        await status_msg.edit_text("❌ Xabar tarqatishda xato yuz berdi")

    await state.clear()


@dp.message(F.text.in_({"⛓ Kanallar ro'yxati", "🔖 Kanallar ro'yxati"}), IsBotAdminFilter(ADMINS))
async def show_channels(message: Message) -> None:
    try:
        channels = db.select_all_channels(detailed=True)
        if not channels:
            await message.answer("⚠️ Kanal mavjud emas")
            return

        await message.answer(
            _format_channels_list(channels),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as error:
        logger.error("Failed to show channels: %s", error)
        await message.answer("❌ Kanallar ro'yxatini olib bo'lmadi")


@dp.message(F.text == "🛡 Adminlar ro'yxati", IsBotAdminFilter(ADMINS))
async def show_admins_list(message: Message) -> None:
    admins = db.list_admins_with_names()
    if not admins:
        await message.answer("⚠️ Adminlar ro'yxati bo'sh.")
        return

    text = "🛡 <b>Adminlar ro'yxati</b>\n\n"
    for index, (admin_id, full_name) in enumerate(admins, 1):
        role = "Super admin" if admin_id in ADMINS else "Cheklangan admin"
        display_name = full_name or "Noma'lum"
        text += (
            f"{index}. <a href='tg://user?id={admin_id}'>{display_name}</a>\n"
            f"🆔 <code>{admin_id}</code>\n"
            f"🔐 {role}\n\n"
        )

    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "👤 Yangi admin qo'shish", IsSuperAdminFilter(ADMINS))
async def add_admin_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminState.add_admin)
    await message.answer(
        "👤 Yangi admin uchun foydalanuvchi ID yuboring yoki uning xabarini forward qiling.\n\n"
        "Yangi qo'shilgan admin cheklangan huquqlarda bo'ladi.\n"
        "Bekor qilish uchun `🚫 Bekor qilish` ni bosing.",
        reply_markup=admin_keyboard.support_cancel_keyboard(),
        parse_mode="Markdown",
    )


@dp.message(AdminState.add_admin, IsSuperAdminFilter(ADMINS))
async def add_admin_finish(message: Message, state: FSMContext) -> None:
    if message.text == "🚫 Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=_admin_menu_markup(message.from_user.id))
        return

    target_user_id = await _extract_target_user_id(message)

    if target_user_id is None:
        await message.answer(
            "❌ To'g'ri foydalanuvchi ma'lumotini yuboring.\n\n"
            "Variantlar:\n"
            "1️⃣ Raqamli ID\n"
            "2️⃣ Forward qilingan xabar\n"
            "3️⃣ <code>tg://user?id=123...</code>\n"
            "4️⃣ <code>https://t.me/AkaStarsBot?start=123...</code> kabi start link",
            parse_mode="HTML",
        )
        return

    if db.is_admin(target_user_id) or target_user_id in set(ADMINS):
        await message.answer(
            "ℹ️ Bu foydalanuvchi allaqachon admin.\n\n"
            f"🆔 ID: <code>{target_user_id}</code>",
            parse_mode="HTML",
        )
        return

    db.add_admin(target_user_id)
    await state.clear()
    await message.answer(
        "✅ Yangi admin qo'shildi.\n\n"
        f"🆔 ID: <code>{target_user_id}</code>\n"
        "🔒 Bu admin super-admin emas, ya'ni boshqa admin qo'sha olmaydi yoki olib tashlay olmaydi.",
        reply_markup=_admin_menu_markup(message.from_user.id),
        parse_mode="HTML",
    )


@dp.message(F.text == "🚫 Adminlikdan olish", IsSuperAdminFilter(ADMINS))
async def remove_admin_start(message: Message) -> None:
    removable_admins = db.list_removable_admins_with_names(ADMINS)
    if not removable_admins:
        await message.answer("ℹ️ Olib tashlash mumkin bo'lgan cheklangan adminlar hozircha yo'q.")
        return

    text = "🚫 <b>Adminlikdan olish</b>\n\nKerakli adminni tanlang:"
    keyboard = admin_keyboard.removable_admins_keyboard(
        [(admin_id, full_name or str(admin_id)) for admin_id, full_name in removable_admins]
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@dp.callback_query(F.data == "admins_close", IsSuperAdminFilter(ADMINS))
async def close_admins_manage(call: CallbackQuery) -> None:
    await call.message.delete()
    await call.answer()


@dp.callback_query(F.data.startswith("admin_remove:"), IsSuperAdminFilter(ADMINS))
async def remove_admin_callback(call: CallbackQuery) -> None:
    target_admin_id = int(call.data.split(":", 1)[1])
    if target_admin_id in ADMINS:
        await call.answer(".env dagi super adminni olib bo'lmaydi.", show_alert=True)
        return

    db.remove_admin(target_admin_id)
    await call.answer("Adminlik olib tashlandi.", show_alert=True)
    await call.message.edit_text(
        "✅ Adminlik olib tashlandi.\n\n"
        f"🆔 <code>{target_admin_id}</code>",
        parse_mode="HTML",
    )


@dp.message(F.text == "➕ Kanal qo'shish", IsBotAdminFilter(ADMINS))
async def add_channel_start(message: Message, state: FSMContext) -> None:
    await state.set_state(ChannelState.kanal_qoshish)
    await state.update_data(channel_mode="regular")
    logger.info("Regular channel add started by admin %s", message.from_user.id)
    await message.answer(
        "➕ Oddiy majburiy kanal yoki guruh qo'shish.\n\n"
        "Avval kanal yoki guruhni tanlang.\n"
        "Keyingi qadamda xohlasangiz private `+invite` linkni ham bog'lab berasiz.",
        reply_markup=admin_keyboard.channel_request_keyboard(),
        parse_mode="Markdown",
    )


@dp.message(F.text == "🎯 Zayafkali kanal qo'shish", IsBotAdminFilter(ADMINS))
async def add_join_request_channel_start(message: Message, state: FSMContext) -> None:
    await state.set_state(ChannelState.kanal_qoshish)
    await state.update_data(channel_mode="join_request")
    logger.info("Join-request channel add started by admin %s", message.from_user.id)
    await message.answer(
        "🎯 Zayafkali majburiy kanal qo'shish.\n\n"
        "Bot bu kanal uchun join-request link yaratadi va belgilangan sondagi odam qo'shilgach "
        "uni majburiy kanallar ro'yxatidan avtomatik chiqaradi.",
        reply_markup=admin_keyboard.channel_request_keyboard(),
    )


@dp.message(ChannelState.kanal_qoshish, IsBotAdminFilter(ADMINS))
async def add_channel(message: Message, state: FSMContext) -> None:
    try:
        if message.text == "↩️ Admin menyuga qaytish":
            await state.clear()
            await message.answer("🔐 Admin menyu", reply_markup=_admin_menu_markup(message.from_user.id))
            return

        if message.text == "🔢 ID yuborish":
            await message.answer(
                "Kanal yoki guruh ID sini yuboring.\nMasalan: <code>-1001234567890</code>",
                parse_mode="HTML",
            )
            return

        if message.text == "📝 Username yuborish":
            await message.answer(
                "Kanal yoki guruh username sini yuboring.\nMasalan: <code>@my_channel</code>",
                parse_mode="HTML",
            )
            return

        if message.text == "🔗 Link yuborish":
            await message.answer(
                "Havolani yuboring.\n\n"
                "Qo'llab-quvvatlanadi:\n"
                "1️⃣ Kanal public linki\n"
                "2️⃣ Private <code>https://t.me/+...</code> invite link\n"
                "3️⃣ Bot/start link, masalan <code>https://t.me/AkaStarsBot?start=123</code>\n"
                "4️⃣ Oddiy <code>https://...</code> link\n\n"
                "Agar havoladan kanalni aniqlab bo'lmasa, bot uni saqlab qoladi va keyin sizdan "
                "qaysi kanalga bog'lanishini tanlashni so'raydi.",
                parse_mode="HTML",
            )
            return

        if message.text and _is_bot_start_link(message.text):
            standalone_link = message.text.strip()
            link_name = _build_external_link_name(standalone_link)
            db.add_channel(
                _generate_external_link_id(),
                link_name,
                standalone_link,
                channel_mode="external_link",
                is_enabled=True,
            )
            await state.clear()
            await message.answer(
                "✅ Bot link qo'shildi!\n\n"
                f"📛 Nomi: <b>{link_name}</b>\n"
                "🧩 Turi: <b>Bot/start link</b>\n"
                f"🔗 <a href='{standalone_link}'>Saqlangan havola</a>\n\n"
                "Bu havola foydalanuvchilarga ko'rsatiladi. Obuna tekshiruvi esa faqat haqiqiy kanal/guruhlar uchun ishlaydi.",
                reply_markup=_admin_menu_markup(message.from_user.id),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            logger.info("Standalone bot link added: %s", standalone_link)
            return

        if message.text and _is_custom_action_link(message.text):
            await state.update_data(pending_channel_custom_link=message.text.strip())
            await message.answer(
                "🔗 Havola saqlandi.\n\n"
                "Endi shu havola qaysi kanal yoki guruhga tegishli bo'lsa, o'shani tanlang yoki username/ID orqali yuboring.\n"
                "Foydalanuvchilarga aynan shu havola ko'rsatiladi, obuna tekshiruvi esa haqiqiy kanal ID orqali ishlaydi.",
                reply_markup=admin_keyboard.channel_request_keyboard(),
            )
            return

        chat = await _resolve_target_chat(message)
        bot_user = await bot.get_me()
        await _ensure_bot_access(chat.id, bot_user.id)

        state_data = await state.get_data()
        channel_mode = state_data.get("channel_mode", "regular")
        channel_name = chat.title or chat.full_name or str(chat.id)
        pending_custom_link = state_data.get("pending_channel_custom_link")

        if channel_mode == "join_request":
            await state.set_state(ChannelState.target_count)
            await state.update_data(pending_channel_id=chat.id, pending_channel_name=channel_name)
            await message.answer(
                "🎯 Nechta foydalanuvchi qo'shilgach bu kanal majburiy ro'yxatdan chiqarilsin?\n\n"
                "Masalan: <code>10</code>\n\n"
                "Bekor qilish uchun `🚫 Bekor qilish` ni bosing.",
                parse_mode="HTML",
                reply_markup=admin_keyboard.support_cancel_keyboard(),
            )
            return

        invite_link = await _get_invite_link(chat.id)
        if pending_custom_link:
            db.add_channel(chat.id, channel_name, pending_custom_link, channel_mode="regular", is_enabled=True)
            await state.clear()
            await message.answer(
                "✅ Kanal qo'shildi!\n\n"
                f"📛 Nomi: <b>{channel_name}</b>\n"
                "🧩 Turi: <b>Oddiy majburiy kanal</b>\n"
                f"🔗 <a href='{pending_custom_link}'>Saqlangan private/public link</a>",
                reply_markup=_admin_menu_markup(message.from_user.id),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            logger.info("Regular channel added with pre-supplied link: %s - %s", chat.id, channel_name)
            return

        await state.set_state(ChannelState.private_link)
        await state.update_data(
            pending_channel_id=chat.id,
            pending_channel_name=channel_name,
            pending_channel_default_link=invite_link,
        )
        await message.answer(
            "🔗 Endi ushbu kanal uchun foydalanuvchilarga ko'rsatiladigan havolani yuboring.\n\n"
            "Bu yerga private invite link, bot/start link yoki oddiy <code>https://...</code> havola yuborishingiz mumkin.\n"
            "Agar kerak bo'lmasa, <b>⏭ O'tkazib yuborish</b> ni bosing va bot default kanal linkini saqlaydi.",
            reply_markup=admin_keyboard.optional_link_keyboard(),
            parse_mode="HTML",
        )
    except Exception as error:
        logger.error("Failed to add channel: %s", error)
        await message.answer(
            f"❌ Xato: {error}\n\n"
            "Qadamlar:\n"
            "1️⃣ Botni kanal yoki guruhga qo'shing\n"
            "2️⃣ Botga admin huquqlari bering\n"
            "3️⃣ Pastdagi tugmadan kanal yoki guruhni qayta tanlang yoki username/ID/link yuboring",
            reply_markup=admin_keyboard.channel_request_keyboard(),
        )


@dp.message(ChannelState.private_link, IsBotAdminFilter(ADMINS))
async def add_channel_private_link(message: Message, state: FSMContext) -> None:
    if message.text == "🚫 Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=_admin_menu_markup(message.from_user.id))
        return

    state_data = await state.get_data()
    channel_id = state_data["pending_channel_id"]
    channel_name = state_data["pending_channel_name"]
    default_link = state_data["pending_channel_default_link"]

    if message.text == "🔗 Link yuborish":
        await message.answer(
            "Havolani matn ko'rinishida yuboring.\n"
            "Masalan:\n"
            "<code>https://t.me/+abc...</code>\n"
            "<code>https://t.me/my_channel</code>\n"
            "<code>https://t.me/AkaStarsBot?start=123</code>",
            parse_mode="HTML",
        )
        return

    if message.text == "⏭ O'tkazib yuborish":
        selected_link = default_link
    else:
        selected_link = (message.text or "").strip()
        if not _is_supported_custom_link(selected_link):
            await message.answer(
                "❌ Havola noto'g'ri formatda.\n\n"
                "To'g'ri misollar:\n"
                "<code>https://t.me/+abcDEF123</code>\n"
                "<code>https://t.me/my_channel</code>\n"
                "<code>https://t.me/AkaStarsBot?start=123</code>\n"
                "<code>https://example.com/page</code>",
                parse_mode="HTML",
            )
            return

    db.add_channel(channel_id, channel_name, selected_link, channel_mode="regular", is_enabled=True)
    await state.clear()
    await message.answer(
        "✅ Kanal qo'shildi!\n\n"
        f"📛 Nomi: <b>{channel_name}</b>\n"
        "🧩 Turi: <b>Oddiy majburiy kanal</b>\n"
        f"🔗 <a href='{selected_link}'>Saqlangan link</a>",
        reply_markup=_admin_menu_markup(message.from_user.id),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    logger.info("Regular channel added with custom link: %s - %s", channel_id, channel_name)


@dp.message(ChannelState.target_count, IsBotAdminFilter(ADMINS))
async def add_join_request_channel_finish(message: Message, state: FSMContext) -> None:
    if message.text == "🚫 Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=_admin_menu_markup(message.from_user.id))
        return

    if not message.text or not message.text.strip().isdigit():
        await message.answer("❌ Faqat musbat butun son yuboring. Masalan: <code>10</code>", parse_mode="HTML")
        return

    target_count = int(message.text.strip())
    if target_count <= 0 or target_count > 1_000_000:
        await message.answer("❌ Maqsad soni 1 dan 1000000 gacha bo'lishi kerak.")
        return

    state_data = await state.get_data()
    channel_id = state_data["pending_channel_id"]
    channel_name = state_data["pending_channel_name"]

    try:
        invite_link = await _get_invite_link(channel_id, join_request=True, target_count=target_count)
        db.add_channel(
            channel_id,
            channel_name,
            invite_link,
            channel_mode="join_request",
            target_count=target_count,
            joined_count=0,
            is_enabled=True,
        )
        await message.answer(
            "✅ Zayafkali kanal qo'shildi!\n\n"
            f"📛 Nomi: <b>{channel_name}</b>\n"
            "🧩 Turi: <b>Zayafkali majburiy kanal</b>\n"
            f"🎯 Maqsad: <b>{target_count}</b> ta foydalanuvchi\n"
            f"🔗 <a href='{invite_link}'>Join-request link</a>\n\n"
            "Maqsad to'lgach bu kanal majburiy obuna ro'yxatidan avtomatik chiqariladi.",
            reply_markup=_admin_menu_markup(message.from_user.id),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        logger.info("Join-request channel added: %s target=%s", channel_id, target_count)
    except Exception as error:
        logger.error("Failed to finalize join-request channel: %s", error)
        await message.answer(
            f"❌ Xato: {error}",
            reply_markup=_admin_menu_markup(message.from_user.id),
        )
    finally:
        await state.clear()


@dp.callback_query(F.data.in_({"add_forward", "add_id", "add_username", "add_link"}), IsBotAdminFilter(ADMINS))
async def channel_add_help(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ChannelState.kanal_qoshish)
    instructions = {
        "add_forward": "📌 Kanaldan biror postni <b>forward</b> qiling.",
        "add_id": "🔢 Kanal ID sini yuboring (masalan: -1001234567890).",
        "add_username": "📝 Kanal username yuboring (masalan: @mychannel).",
        "add_link": "🔗 Kanal public linkini yuboring (masalan: https://t.me/mychannel).",
    }
    await call.message.answer(instructions.get(call.data, "Ma'lumot yuboring."), parse_mode="HTML")
    await call.answer()


@dp.message(F.text == "➖ Kanal o'chirish", IsBotAdminFilter(ADMINS))
async def delete_channel_start(message: Message, state: FSMContext) -> None:
    try:
        channels = db.select_all_channels(detailed=True)
        if not channels:
            await message.answer("⚠️ O'chirish uchun kanal mavjud emas")
            return

        await state.set_state(DelChannelState.delete_channel)
        text = "➖ <b>O'chirilishi kerak bo'lgan kanallarni tanlang:</b>\n\n"
        for index, (_, channel_name, _, channel_mode, target_count, joined_count, is_enabled) in enumerate(channels, 1):
            if channel_mode == "join_request":
                mode_label = "🎯 Zayafkali"
            elif channel_mode == "external_link":
                mode_label = "🤖 Bot link"
            else:
                mode_label = "📢 Oddiy"
            status_label = "🟢 Faol" if is_enabled else "⚪️ O'chirilgan"
            progress = f" ({joined_count}/{target_count})" if channel_mode == "join_request" else ""
            text += f"{index}. {channel_name} - {mode_label} {status_label}{progress}\n"

        await message.answer(
            text,
            reply_markup=admin_keyboard.inline_wars_btn(channels),
            parse_mode="HTML",
        )
    except Exception as error:
        logger.error("Failed to start delete channel: %s", error)
        await message.answer("❌ Kanallar ro'yxatini olib bo'lmadi")


@dp.callback_query(F.data == "back_admin", DelChannelState.delete_channel)
async def back_to_admin(call: CallbackQuery, state: FSMContext) -> None:
    await call.message.delete()
    await state.clear()
    await call.message.answer("🔐 Admin menyu", reply_markup=_admin_menu_markup(call.from_user.id))
    await call.answer()


@dp.callback_query(F.data.startswith("video_"), IsBotAdminFilter(ADMINS))
async def handle_video_admin_actions(call: CallbackQuery, state: FSMContext) -> None:
    action, user_id_raw = call.data.split(":", 1)
    target_user_id = int(user_id_raw)

    if action == "video_ban":
        db.ban_user(target_user_id, banned_by=call.from_user.id)
        await call.answer("Foydalanuvchi ban qilindi.", show_alert=True)
        await call.message.reply(
            f"⛔ Foydalanuvchi ban qilindi.\n🆔 ID: <code>{target_user_id}</code>",
            parse_mode="HTML",
        )
        try:
            await bot.send_message(
                chat_id=target_user_id,
                text="⛔ Siz botdan foydalanishdan chetlatildingiz.",
            )
        except Exception:
            pass
        return

    mode = "notify" if action == "video_notify" else "ask"
    target_state = SupportState.notify_message if mode == "notify" else SupportState.ask_message
    await state.set_state(target_state)
    await state.update_data(target_user_id=target_user_id, mode=mode)

    if mode == "ask":
        text = (
            "❇️ Xabaringizni kiriting.\n\n"
            "❔ Foydalanuvchidan so'rang:\n"
            "Ikki tomonlama aloqa.\n"
            "Ushbu rejim foydalanuvchiga BIR xabarda javob berish imkonini beradi.\n\n"
            "Agar fikringizni o'zgartirsangiz, \"🚫 Bekor qilish\" tugmasini bosing."
        )
    else:
        text = (
            "❇️ Xabaringizni kiriting.\n\n"
            "❕ Foydalanuvchini xabardor qiling:\n"
            "Bir tomonlama aloqa.\n"
            "Bu rejimda foydalanuvchi javob bera olmaydi.\n\n"
            "Agar fikringizni o'zgartirsangiz, \"🚫 Bekor qilish\" tugmasini bosing."
        )

    await call.message.answer(text, reply_markup=admin_keyboard.support_cancel_keyboard())
    await call.answer()


@dp.message(SupportState.notify_message, IsBotAdminFilter(ADMINS))
@dp.message(SupportState.ask_message, IsBotAdminFilter(ADMINS))
async def send_support_message(message: Message, state: FSMContext) -> None:
    if message.text == "🚫 Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=_admin_menu_markup(message.from_user.id))
        return

    state_data = await state.get_data()
    target_user_id = state_data["target_user_id"]
    mode = state_data["mode"]

    try:
        await bot.copy_message(
            chat_id=target_user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )

        if mode == "ask":
            db.open_support_thread(target_user_id, message.from_user.id, "ask")
            await bot.send_message(
                chat_id=target_user_id,
                text="✍️ Admin savol yubordi. Javobingizni bitta xabar bilan yuborishingiz mumkin.",
            )
            await message.answer(
                "✅ Savol yuborildi. Endi foydalanuvchi bitta xabar bilan javob bera oladi.",
                reply_markup=_admin_menu_markup(message.from_user.id),
            )
        else:
            await message.answer(
                "✅ Xabar foydalanuvchiga yuborildi.",
                reply_markup=_admin_menu_markup(message.from_user.id),
            )
    except TelegramAPIError as error:
        logger.error("Failed to send support message: %s", error)
        await message.answer("❌ Xabarni yuborib bo'lmadi.", reply_markup=ReplyKeyboardRemove())
        return

    await state.clear()


@dp.callback_query(DelChannelState.delete_channel)
async def delete_channel(call: CallbackQuery, state: FSMContext) -> None:
    await call.message.delete()
    channel_id = int(call.data)
    channel = db.get_channel(channel_id)
    channel_name = channel[1] if channel else str(channel_id)
    try:
        chat = await bot.get_chat(call.data)
        channel_name = chat.title or chat.full_name or channel_name
        db.delete_channel(channel_id)
        await call.message.answer(
            "✅ Kanal o'chirildi!\n\n"
            f"📛 Nomi: <b>{channel_name}</b>",
            parse_mode="HTML",
        )
    except Exception as error:
        logger.warning("Channel metadata fetch failed during delete, deleting directly: %s", error)
        try:
            db.delete_channel(channel_id)
            await call.message.answer(
                "✅ Kanal o'chirildi!\n\n"
                f"📛 Nomi: <b>{channel_name}</b>",
                parse_mode="HTML",
            )
        except Exception as inner_error:
            logger.error("Failed to delete channel: %s", inner_error)
            await call.message.answer(f"❌ Xato: {inner_error}")

    await state.clear()
    await call.message.answer("🔐 Admin menyu", reply_markup=_admin_menu_markup(call.from_user.id))
    await call.answer()


async def _resolve_target_chat(message: Message):
    if message.chat_shared:
        return await bot.get_chat(message.chat_shared.chat_id)

    if message.forward_from_chat:
        return await bot.get_chat(message.forward_from_chat.id)

    if message.text:
        chat_reference = _normalize_chat_reference(message.text.strip())
        if chat_reference is None:
            raise ValueError(
                "🔒 `t.me/+...` private invite link orqali kanalni avtomatik topib bo'lmaydi.\n\n"
                "Iltimos, quyidagilardan birini qiling:\n"
                "1️⃣ `📢 Mening kanalni tanlash` tugmasidan foydalaning\n"
                "2️⃣ Kanaldan bitta postni forward qiling\n"
                "3️⃣ Kanal username yoki ID yuboring"
            )
        return await bot.get_chat(chat_reference)

    raise ValueError("Kanal yoki guruh aniqlanmadi. Tugma orqali tanlang yoki username/ID yuboring.")


def _normalize_chat_reference(raw_value: str) -> str | None:
    value = raw_value.strip()
    if value.startswith("@"):
        return value
    if value.startswith("-100") and value[4:].isdigit():
        return value
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return value
    if value.startswith("https://t.me/") or value.startswith("http://t.me/"):
        parsed = urlparse(value)
        if _is_bot_start_link(value):
            return None
        slug = parsed.path.strip("/")
        if not slug or slug.startswith("+") or slug.startswith("joinchat/"):
            return None
        return f"@{slug.split('/', 1)[0]}"
    return value


async def _extract_target_user_id(message: Message) -> int | None:
    forward_from_user = getattr(message, "forward_from_user", None)
    if forward_from_user:
        return forward_from_user.id

    forward_origin = getattr(message, "forward_origin", None)
    if forward_origin and hasattr(forward_origin, "sender_user") and forward_origin.sender_user:
        return forward_origin.sender_user.id

    text = (message.text or "").strip()
    if not text:
        return None

    if text.isdigit():
        return int(text)

    if text.startswith("tg://user"):
        parsed = urlparse(text)
        user_id = parse_qs(parsed.query).get("id", [None])[0]
        if user_id and user_id.isdigit():
            return int(user_id)

    if text.startswith("https://t.me/") or text.startswith("http://t.me/"):
        parsed = urlparse(text)
        query = parse_qs(parsed.query)
        start_value = query.get("start", [None])[0]
        if start_value and start_value.isdigit():
            return int(start_value)

        slug = parsed.path.strip("/")
        if slug and not slug.startswith("+") and slug != "joinchat":
            try:
                chat = await bot.get_chat(f"@{slug.split('/', 1)[0]}")
            except TelegramAPIError:
                return None
            return getattr(chat, "id", None)

    return None


def _is_supported_channel_link(raw_value: str) -> bool:
    value = raw_value.strip()
    return (
        value.startswith("https://t.me/+")
        or value.startswith("http://t.me/+")
        or value.startswith("https://t.me/")
        or value.startswith("http://t.me/")
    )


def _is_private_invite_link(raw_value: str) -> bool:
    value = raw_value.strip()
    return value.startswith("https://t.me/+") or value.startswith("http://t.me/+")


def _is_bot_start_link(raw_value: str) -> bool:
    value = raw_value.strip()
    if not (value.startswith("https://t.me/") or value.startswith("http://t.me/")):
        return False

    parsed = urlparse(value)
    query = parse_qs(parsed.query)
    return any(key in query for key in ("start", "startgroup", "startapp"))


def _is_http_url(raw_value: str) -> bool:
    value = raw_value.strip()
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_supported_custom_link(raw_value: str) -> bool:
    value = raw_value.strip()
    return bool(value) and _is_http_url(value)


def _is_custom_action_link(raw_value: str) -> bool:
    value = raw_value.strip()
    return _is_private_invite_link(value) or _is_bot_start_link(value) or (
        _is_http_url(value) and _normalize_chat_reference(value) is None
    )


def _generate_external_link_id() -> int:
    return -(time_ns() // 1000)


def _build_external_link_name(raw_value: str) -> str:
    parsed = urlparse(raw_value.strip())
    slug = parsed.path.strip("/").split("/", 1)[0]
    if slug:
        return f"🤖 {slug}"
    return "🤖 Bot link"


async def _ensure_bot_access(chat_id: int, bot_id: int) -> None:
    try:
        member = await bot.get_chat_member(chat_id, bot_id)
    except TelegramAPIError as error:
        raise ValueError("Bot kanal yoki guruhga qo'shilmagan.") from error

    if getattr(member, "status", None) in {"left", "kicked"}:
        raise ValueError("Bot kanal yoki guruhga qo'shilmagan.")


async def _get_invite_link(chat_id: int, join_request: bool = False, target_count: int = 0) -> str:
    chat = await bot.get_chat(chat_id)
    if join_request:
        try:
            invite_link = await bot.create_chat_invite_link(
                chat_id=chat_id,
                creates_join_request=True,
                name=f"Maqsadli oqim {target_count} ta",
            )
            return invite_link.invite_link
        except TelegramAPIError as error:
            raise ValueError(
                "Zayafkali invite link yaratib bo'lmadi. Bot admin bo'lishi va invite link yaratish huquqiga ega bo'lishi kerak."
            ) from error

    if chat.username:
        return f"https://t.me/{chat.username}"

    try:
        return await bot.export_chat_invite_link(chat_id)
    except TelegramAPIError as error:
        raise ValueError(
            "Invite link olib bo'lmadi. Bot admin bo'lishi va invite link yaratish huquqiga ega bo'lishi kerak."
        ) from error


def _format_channels_list(channels) -> str:
    text = "🔖 <b>Kanallar ro'yxati</b>\n\n"
    for index, (channel_id, channel_name, channel_link, channel_mode, target_count, joined_count, is_enabled) in enumerate(channels, 1):
        if channel_mode == "join_request":
            mode_label = "🎯 Zayafkali"
        elif channel_mode == "external_link":
            mode_label = "🤖 Bot link"
        else:
            mode_label = "📢 Oddiy"
        if channel_mode == "join_request" and not is_enabled and target_count > 0 and joined_count >= target_count:
            status_label = "✅ Maqsadga yetgan"
        else:
            status_label = "🟢 Faol" if is_enabled else "⚪️ Nofaol"

        text += (
            f"<b>{index}.</b> {channel_name}\n"
            f"🆔 <code>{channel_id}</code>\n"
            f"🧩 {mode_label}\n"
            f"📍 Holat: {status_label}\n"
        )
        if channel_mode == "join_request":
            text += f"📈 Jarayon: <b>{joined_count}/{target_count}</b>\n"
        text += f"🔗 <a href='{channel_link}'>Link</a>\n\n"
    return text


def _format_bot_created_at(raw_value: str | None) -> str:
    if not raw_value:
        return "Noma'lum"
    try:
        return datetime.fromisoformat(raw_value).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return raw_value
