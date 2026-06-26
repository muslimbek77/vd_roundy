import logging

from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatJoinRequest, ChatMemberUpdated

from loader import bot, db, dp
from utils.misc.admin_notify import send_admin_message

logger = logging.getLogger(__name__)


@dp.chat_join_request()
async def handle_target_channel_join_request(join_request: ChatJoinRequest) -> None:
    channel = db.get_channel(join_request.chat.id)
    if not channel:
        return

    channel_id, channel_name, channel_link, channel_mode, target_count, joined_count, is_enabled = channel
    if not is_enabled:
        return

    logger.info(
        "Join request received for channel %s from user %s",
        channel_id,
        join_request.from_user.id,
    )

    inserted = db.record_channel_join(channel_id, join_request.from_user.id)
    if inserted and channel_mode == "join_request":
        await _handle_channel_progress(channel_id, channel_name)

    if channel_mode == "join_request":
        try:
            await bot.approve_chat_join_request(
                chat_id=join_request.chat.id,
                user_id=join_request.from_user.id,
            )
        except TelegramAPIError as error:
            logger.error("Failed to approve join request for channel %s: %s", channel_id, error)
            return

    if not inserted:
        logger.info(
            "Join request for channel %s from user %s was not inserted into ChannelJoins",
            channel_id,
            join_request.from_user.id,
        )


@dp.chat_member()
async def handle_target_channel_member_update(update: ChatMemberUpdated) -> None:
    channel = db.get_channel(update.chat.id)
    if not channel:
        return

    channel_id, channel_name, _, channel_mode, _, _, is_enabled = channel
    if not is_enabled:
        return

    old_status = getattr(update.old_chat_member, "status", None)
    new_status = getattr(update.new_chat_member, "status", None)
    if new_status not in {"member", "administrator", "creator"}:
        return

    if old_status in {"member", "administrator", "creator"}:
        return

    logger.info(
        "Chat member update counted for channel %s from user %s: %s -> %s",
        channel_id,
        update.new_chat_member.user.id,
        old_status,
        new_status,
    )
    if db.record_channel_join(channel_id, update.new_chat_member.user.id) and channel_mode == "join_request":
        await _handle_channel_progress(channel_id, channel_name)


async def _handle_channel_progress(channel_id: int, channel_name: str) -> None:
    channel = db.get_channel(channel_id)
    if not channel:
        return

    _, _, channel_link, _, target_count, joined_count, is_enabled = channel
    logger.info(
        "Join-request progress updated for channel %s: %s/%s",
        channel_id,
        joined_count,
        target_count,
    )

    if is_enabled and target_count > 0 and joined_count >= target_count:
        db.disable_channel(channel_id)
        try:
            await bot.revoke_chat_invite_link(chat_id=channel_id, invite_link=channel_link)
        except TelegramAPIError as error:
            logger.warning("Failed to revoke invite link for channel %s: %s", channel_id, error)

        await send_admin_message(
            "✅ Zayafkali kanal maqsadga yetdi va majburiy ro'yxatdan chiqarildi.\n\n"
            f"📛 Kanal: {channel_name}\n"
            f"🆔 ID: <code>{channel_id}</code>\n"
            f"📈 Natija: <b>{joined_count}/{target_count}</b>"
        )
