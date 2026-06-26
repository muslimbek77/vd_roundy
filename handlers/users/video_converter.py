import logging

from aiogram import F
from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile, Message

from loader import db, dp
from utils.misc.admin_notify import notify_video_submission
from utils.video.converter import (
    ConversionError,
    cleanup_temp_dir,
    convert_video_note_to_video,
    convert_video_to_video_note,
)

logger = logging.getLogger(__name__)


@dp.message(F.chat.type == "private", F.video)
async def handle_video_to_note(message: Message) -> None:
    status_message = await message.answer("⏳ Video yumaloq formatga o'tkazilmoqda...")
    result = None

    try:
        db.touch_user(message.from_user.id, message.from_user.full_name or "Unknown")
        await notify_video_submission(message, "Oddiy video -> yumaloq video")
        result = await convert_video_to_video_note(
            message.bot,
            message.video.file_id,
            duration_seconds=message.video.duration or 0,
        )
        for note_path in result.paths:
            await message.answer_video_note(video_note=FSInputFile(note_path))
        await status_message.edit_text(
            f"✅ Tayyor! {len(result.paths)} ta yumaloq video yuborildi."
        )
    except ConversionError as error:
        logger.warning("Video to video_note conversion failed: %s", error)
        error_text = str(error)
        if "too long" in error_text.lower():
            await status_message.edit_text(
                "❌ Video 3 daqiqadan uzun. Iltimos, 3 daqiqagacha bo'lgan video yuboring."
            )
        else:
            await status_message.edit_text(
                "❌ Bu videoni qayta ishlashning imkoni bo'lmadi. "
                "Iltimos, boshqa videoni yuborib qayta urinib ko'ring."
            )
    except TelegramAPIError as error:
        logger.warning("Telegram API error while sending video_note: %s", error)
        await status_message.edit_text(_humanize_delivery_error(error))
    except Exception as error:
        logger.exception("Unexpected error during video to video_note conversion: %s", error)
        await status_message.edit_text(
            "❌ Kutilmagan xatolik yuz berdi. Iltimos, birozdan keyin qayta urinib ko'ring."
        )
    finally:
        if result:
            cleanup_temp_dir(result.temp_dir)


@dp.message(F.chat.type == "private", F.video_note)
async def handle_video_note_to_video(message: Message) -> None:
    status_message = await message.answer("⏳ Yumaloq video oddiy formatga o'tkazilmoqda...")
    result = None

    try:
        db.touch_user(message.from_user.id, message.from_user.full_name or "Unknown")
        await notify_video_submission(message, "Yumaloq video -> oddiy MP4")
        result = await convert_video_note_to_video(message.bot, message.video_note.file_id)
        await message.answer_video(
            video=FSInputFile(result.path),
            supports_streaming=True,
            caption="✅ Tayyor MP4 video",
        )
        await status_message.edit_text("✅ Tayyor! Oddiy video yuborildi.")
    except ConversionError as error:
        logger.warning("Video_note to video conversion failed: %s", error)
        await status_message.edit_text(
            "❌ Bu yumaloq videoni qayta ishlashning imkoni bo'lmadi. "
            "Iltimos, boshqa fayl bilan qayta urinib ko'ring."
        )
    except TelegramAPIError as error:
        logger.warning("Telegram API error while sending video: %s", error)
        await status_message.edit_text(_humanize_delivery_error(error))
    except Exception as error:
        logger.exception("Unexpected error during video_note to video conversion: %s", error)
        await status_message.edit_text(
            "❌ Kutilmagan xatolik yuz berdi. Iltimos, birozdan keyin qayta urinib ko'ring."
        )
    finally:
        if result:
            cleanup_temp_dir(result.temp_dir)


@dp.message(F.chat.type == "private")
async def handle_unsupported_private_message(message: Message) -> None:
    if message.text and message.text.startswith("/"):
        return

    thread = db.get_open_support_thread(message.from_user.id)
    if thread:
        _, admin_id, mode = thread
        if mode == "ask":
            try:
                await message.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        "📩 Foydalanuvchidan javob keldi.\n\n"
                        f"🆔 ID: <code>{message.from_user.id}</code>\n"
                        f"👤 Ism: {message.from_user.full_name or 'Nomaʼlum'}"
                    ),
                    parse_mode="HTML",
                )
                await message.bot.copy_message(
                    chat_id=admin_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                )
                db.close_support_thread(message.from_user.id)
                await message.answer("✅ Javobingiz adminga yuborildi.")
                return
            except Exception as error:
                logger.exception("Failed to relay support reply: %s", error)
                await message.answer("❌ Javobni yuborishda xatolik yuz berdi.")
                return

    await message.answer(
        "📩 Menga oddiy video yoki yumaloq video yuboring.\n"
        "Shunda men uni kerakli formatga o'tkazib beraman."
    )


def _humanize_delivery_error(error: TelegramAPIError) -> str:
    error_text = str(error).upper()

    if (
        "VOICE_MESSAGES_FORBIDDEN" in error_text
        or "VIDEO_MESSAGES_FORBIDDEN" in error_text
        or "VIDEO_NOTES_FORBIDDEN" in error_text
        or "VIDEO_NOTE" in error_text and "FORBIDDEN" in error_text
        or "AUDIO" in error_text and "FORBIDDEN" in error_text
        or "VOICE" in error_text and "FORBIDDEN" in error_text
        or "VIDEO_MESSAGE" in error_text and "FORBIDDEN" in error_text
        or "PRIVACY" in error_text and "RESTRICT" in error_text
        or "NOT ACCEPT" in error_text and "VIDEO" in error_text
    ):
        return (
            "❌ Sizning Telegram sozlamangizda audio yoki yumaloq video qabul qilish "
            "cheklangan ko'rinadi.\n\n"
            "Iltimos, Telegram sozlamalarida audio/video message qabul qilishni yoqing "
            "va qayta urinib ko'ring."
        )

    if "FILE_IS_TOO_BIG" in error_text or "REQUEST_ENTITY_TOO_LARGE" in error_text:
        return "❌ Video hajmi juda katta. Iltimos, kichikroq video yuboring."

    return (
        "❌ Tayyor faylni yuborishda xatolik yuz berdi. "
        "Iltimos, birozdan keyin qayta urinib ko'ring."
    )
