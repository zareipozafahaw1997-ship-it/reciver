"""
core/scheduler.py
زمان‌بندی وظایف — سبک، بدون کتابخونه خارجی
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("Scheduler")


async def _seconds_until_midnight() -> float:
    """چند ثانیه تا ۰۰:۰۰ UTC مانده"""
    now       = datetime.now(timezone.utc)
    tomorrow  = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return (tomorrow - now).total_seconds()


async def daily_backup_task() -> None:
    """هر شب ۰۰:۰۰ UTC بکاپ می‌گیره — اگه فعال باشه"""
    from database.mongo import MongoDB
    from utils.channel_logger import send_backup_all
    from config import ADMIN_IDS

    # اول صبر کن تا ۰۰:۰۰
    wait = await _seconds_until_midnight()
    logger.info(f"⏰ Scheduler: next backup in {wait/3600:.1f}h")
    await asyncio.sleep(wait)

    while True:
        try:
            channels = await MongoDB.get_channels()
            if channels.get("auto_backup"):
                logger.info("💾 Scheduler: starting daily backup...")
                # اگه کانال ست نشده، به اولین ادمین بفرسته
                send_to = ADMIN_IDS[0] if ADMIN_IDS else None
                sent, failed = await send_backup_all(send_to=send_to)
                logger.info(f"💾 Scheduler: backup done — sent={sent} failed={failed}")
            else:
                logger.info("⏸ Scheduler: auto backup is disabled, skipping")
        except Exception as e:
            logger.error(f"❌ Scheduler backup error: {e}")

        # صبر کن تا ۲۴ ساعت بعد
        await asyncio.sleep(86400)


def start_scheduler() -> asyncio.Task:
    """استارت scheduler — یه task جدا می‌سازه"""
    task = asyncio.create_task(daily_backup_task())
    logger.info("✅ Scheduler started")
    return task
