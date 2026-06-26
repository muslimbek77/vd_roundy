import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import List

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramAPIError

from loader import dp, bot, db, ADMINS
from middlewares.throttling import ThrottlingMiddleware
from middlewares.checksub import BigBrother
from menucommands.set_bot_commands import set_default_commands
from utils.misc.admin_notify import send_admin_message
from utils.misc.backup import backup_scheduler
import handlers

# Logging konfiguratsiyasi
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
backup_task: asyncio.Task | None = None


async def notify_admins(message: str, admins: List[int]) -> None:
    """Adminlarga xabar yuborish"""
    if not admins:
        return
    await send_admin_message(message)


@dp.startup()
async def on_startup_notify(bot: Bot) -> None:
    """Bot ishga tushganini xabarini yuborish"""
    global backup_task
    try:
        logger.info("Bot starting up...")
        db.create_table_users()
        db.create_table_channels()
        db.create_table_channel_joins()
        db.create_table_meta()
        db.create_table_admins()
        db.create_table_bans()
        db.create_table_support_threads()
        db.ensure_admins(ADMINS)
        db.ensure_meta("bot_created_at", datetime.now(timezone.utc).isoformat())
        await set_default_commands(bot)
        if backup_task is None or backup_task.done():
            backup_task = asyncio.create_task(backup_scheduler(), name="daily-backup-scheduler")
        await notify_admins("✅ Bot ishga tushdi...", ADMINS)
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)


@dp.shutdown()
async def on_shutdown_notify(bot: Bot) -> None:
    """Bot ishdan to'xtadi xabarini yuborish"""
    global backup_task
    try:
        logger.info("Bot shutting down...")
        if backup_task and not backup_task.done():
            backup_task.cancel()
            try:
                await backup_task
            except asyncio.CancelledError:
                pass
        await notify_admins("❌ Bot ishdan to'xtadi!", ADMINS)
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


async def main() -> None:
    """Botni ishga tushirish"""
    try:
        logger.info("Configuring middleware...")
        dp.message.middleware(ThrottlingMiddleware(slow_mode_delay=0.5))
        dp.message.middleware(BigBrother())
        
        logger.info("Starting bot polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        
    except Exception as e:
        logger.error(f"Critical error in main: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
        sys.exit(1)
