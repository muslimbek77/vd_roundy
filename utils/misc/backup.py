import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile

from loader import ADMINS, bot, db

logger = logging.getLogger(__name__)

BACKUP_HOUR = 2
BACKUP_MINUTE = 0
BACKUP_TIMEZONE = ZoneInfo("Asia/Tashkent")


def _seconds_until_next_backup() -> float:
    now = datetime.now(BACKUP_TIMEZONE)
    next_run = now.replace(hour=BACKUP_HOUR, minute=BACKUP_MINUTE, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    return max((next_run - now).total_seconds(), 1.0)


async def send_backup_to_super_admins() -> None:
    timestamp = datetime.now(BACKUP_TIMEZONE).strftime("%Y-%m-%d_%H-%M-%S")
    with TemporaryDirectory(prefix="yumaloqbot-backup-") as temp_dir:
        backup_path = Path(temp_dir) / f"yumaloqbot-backup-{timestamp}.json"
        await asyncio.to_thread(db.export_backup, str(backup_path))

        caption = (
            "🗄 Bot backup fayli\n\n"
            f"🕑 Vaqt: {datetime.now(BACKUP_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🧱 Baza turi: {db.db_type}"
        )

        for admin_id in ADMINS:
            try:
                await bot.send_document(
                    chat_id=admin_id,
                    document=FSInputFile(str(backup_path), filename=backup_path.name),
                    caption=caption,
                )
            except TelegramAPIError as error:
                logger.warning("Failed to send backup to super admin %s: %s", admin_id, error)
            except Exception as error:
                logger.exception("Unexpected backup delivery error for %s: %s", admin_id, error)


async def backup_scheduler() -> None:
    while True:
        await asyncio.sleep(_seconds_until_next_backup())
        try:
            await send_backup_to_super_admins()
            logger.info("Scheduled backup sent to %s super admins", len(ADMINS))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.exception("Scheduled backup failed: %s", error)
