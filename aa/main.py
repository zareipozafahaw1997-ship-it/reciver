"""
main.py
نقطه ورود اصلی ربات — همه چیز async
"""

import asyncio
import logging
import sys
from loguru import logger
from telethon import TelegramClient
from config import API_ID, API_HASH, BOT_TOKEN, BOT_NAME, BOT_VERSION
from database.mongo import MongoDB
from database.redis_client import RedisClient
from handlers import register_user_handlers, register_admin_handlers
from core.account_manager import AccountManager
from core.scheduler import start_scheduler
from utils.channel_logger import set_client as set_logger_client

# ── Loguru — همه لاگ‌های stdlib رو هم intercept می‌کنه ──────────
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | {message}",
    level="DEBUG",
    colorize=False,
)

# stdlib logging → loguru
class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

logging.basicConfig(handlers=[InterceptHandler()], level=logging.DEBUG, force=True)
# telethon خیلی verbose نباشه
logging.getLogger("telethon").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)


async def main() -> None:
    print(f"🚀 {BOT_NAME} v{BOT_VERSION} در حال راه‌اندازی...")

    # ── اتصال به دیتابیس‌ها ─────────────────────────────────────
    await MongoDB.connect()
    await RedisClient.connect()

    # ── ساخت کلاینت ربات ────────────────────────────────────────
    client = TelegramClient("bot_session", API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)

    # ── ثبت هندلرها ─────────────────────────────────────────────
    register_user_handlers(client)
    register_admin_handlers(client)

    me = await client.get_me()
    print(f"✅ ربات @{me.username} با موفقیت راه‌اندازی شد!")
    print("─" * 40)

    # ── ست کردن client برای channel_logger ──────────────────────
    set_logger_client(client)

    # ── استارت AccountManager ────────────────────────────────────
    manager = AccountManager.get_instance()
    await manager.load_all()
    print(f"📦 {manager.count()} اکانت لود شد | {manager.connected_count()} متصل")
    print("─" * 40)

    # ── استارت Scheduler ─────────────────────────────────────────
    scheduler_task = start_scheduler()
    try:
        await client.run_until_disconnected()
    finally:
        print("⏳ در حال خاموش کردن...")
        scheduler_task.cancel()
        await manager.stop_all()
        await MongoDB.disconnect()
        await RedisClient.disconnect()
        print("👋 ربات متوقف شد.")


if __name__ == "__main__":
    asyncio.run(main())
