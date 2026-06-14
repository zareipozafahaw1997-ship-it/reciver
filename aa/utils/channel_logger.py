"""
utils/channel_logger.py
ارسال پیام به کانال‌های لاگ (سشن، ارور، فروش)
"""

import logging
import traceback
from datetime import datetime, timezone
from telethon import TelegramClient
from database.mongo import MongoDB

logger = logging.getLogger("ChannelLogger")

# کلاینت ربات — از main.py ست می‌شه
_bot_client: TelegramClient | None = None


def set_client(client: TelegramClient) -> None:
    global _bot_client
    _bot_client = client


async def _resolve_entity(client, channel: str):
    """
    هر فرمتی رو به entity تبدیل می‌کنه:
    - @username / https://t.me/username → string
    - -1001234567890 → int
    - https://t.me/+hash → join و entity برگردون
    """
    if not channel:
        return None
    ch = channel.strip()

    # آیدی عددی
    if ch.lstrip("-").isdigit():
        return int(ch)

    # لینک invite
    if "t.me/+" in ch or "t.me/joinchat" in ch:
        try:
            invite_hash = ch.split("/+")[-1].split("/joinchat/")[-1].strip("/")
            result = await client(
                __import__("telethon.tl.functions.messages", fromlist=["ImportChatInviteRequest"])
                .ImportChatInviteRequest(invite_hash)
            )
            return result.chats[0]
        except Exception:
            # اگه قبلاً عضوه
            try:
                from telethon.tl.functions.messages import CheckChatInviteRequest
                result = await client(CheckChatInviteRequest(invite_hash))
                if hasattr(result, "chat"):
                    return result.chat
            except Exception:
                pass
            return None

    # https://t.me/username
    if ch.startswith("https://t.me/"):
        ch = "@" + ch.replace("https://t.me/", "").split("/")[0].split("?")[0]
    if not ch.startswith("@"):
        ch = "@" + ch.lstrip("@")
    return ch


async def _send(channel_key: str, text: str, file=None) -> bool:
    if not _bot_client:
        logger.error("❌ _send: no bot client")
        return False
    try:
        channels = await MongoDB.get_channels()
        channel  = channels.get(channel_key)
        logger.info(f"📡 _send key={channel_key} val={channel}")
        if not channel:
            logger.warning(f"⚠️ channel {channel_key} not configured")
            return False
        entity = await _resolve_entity(_bot_client, channel)
        if entity is None:
            logger.error(f"❌ cannot resolve: {channel}")
            return False
        await _bot_client.send_message(entity, text, file=file, parse_mode="md")
        logger.info(f"✅ sent to {channel_key}")
        return True
    except Exception as e:
        logger.error(f"❌ ChannelLogger send error ({channel_key}): {e}")
        return False


# ════════════════════════════════════════════════════════════════
#  کانال سشن‌ها
# ════════════════════════════════════════════════════════════════
async def log_new_account(account: dict, session_file_path: str | None = None) -> None:
    """اکانت جدید + سشن فایل به کانال سشن‌ها"""
    fullname = f"{account.get('tg_first_name','')} {account.get('tg_last_name','')}".strip()
    uname    = f"@{account['tg_username']}" if account.get("tg_username") else "ندارد"
    proxy    = account.get("proxy_used")
    proxy_str = f"`{proxy['host']}:{proxy['port']}`" if proxy else "ندارد"
    now      = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    text = (
        f"🆕 **اکانت جدید**\n\n"
        f"👤 نام: **{fullname or '—'}**\n"
        f"📌 یوزرنیم: {uname}\n"
        f"📱 شماره: `{account.get('phone','—')}`\n"
        f"🆔 آیدی تلگرام: `{account.get('tg_id','—')}`\n"
        f"🔖 کد اکانت: `{account.get('account_id','—')}`\n"
        f"👤 مالک: `{account.get('owner_id','—')}`\n"
        f"⚙️ API ID: `{account.get('api_id','—')}`\n"
        f"🌐 پروکسی: {proxy_str}\n"
        f"📅 زمان: `{now}`"
    )

    import os
    file_to_send = None
    if session_file_path and os.path.exists(session_file_path):
        file_to_send = session_file_path

    await _send("sessions_channel", text, file=file_to_send)


async def send_backup_all(owner_id: int | None = None, send_to: int | None = None) -> tuple[int, int]:
    """
    پوشه sessions رو zip می‌کنه و می‌فرسته
    send_to: آیدی کاربر برای ارسال مستقیم (اگه کانال ست نشده)
    """
    import os
    import zipfile
    import asyncio
    import tempfile
    from config import SESSIONS_DIR

    if not _bot_client:
        return 0, 0

    channels = await MongoDB.get_channels()
    channel_raw = channels.get("backup_channel") or channels.get("sessions_channel") or send_to
    if not channel_raw:
        return 0, 0

    channel = await _resolve_entity(_bot_client, str(channel_raw)) if isinstance(channel_raw, str) else channel_raw
    if channel is None:
        return 0, 0

    # ساخت zip در thread جدا
    def _make_zip() -> tuple[str, int]:
        now      = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        zip_name = f"sessions_backup_{now}.zip"
        zip_path = os.path.join(tempfile.gettempdir(), zip_name)
        count    = 0
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # همه فایل‌های sessions/ و sessions/deleted/ رو zip کن
            for root, dirs, files in os.walk(SESSIONS_DIR):
                for fname in files:
                    if fname.startswith("."):
                        continue
                    fpath    = os.path.join(root, fname)
                    arcname  = os.path.relpath(fpath, SESSIONS_DIR)
                    zf.write(fpath, arcname)
                    count += 1
        return zip_path, count

    loop              = asyncio.get_event_loop()
    zip_path, count   = await loop.run_in_executor(None, _make_zip)

    if count == 0:
        try:
            os.remove(zip_path)
        except Exception:
            pass
        return 0, 0

    try:
        now     = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        caption = (
            f"💾 **بکاپ سشن‌ها**\n\n"
            f"📦 تعداد فایل: `{count}`\n"
            f"📅 زمان: `{now}`"
        )
        if owner_id:
            caption += f"\n👤 مالک: `{owner_id}`"

        await _bot_client.send_file(channel, zip_path, caption=caption, parse_mode="md")
        return count, 0

    except Exception as e:
        logger.error(f"❌ Backup zip send error: {e}")
        return 0, 1

    finally:
        try:
            os.remove(zip_path)
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════
#  کانال ارورها
# ════════════════════════════════════════════════════════════════
async def log_error(source: str, error: Exception | str, detail: str = "") -> None:
    """ارسال خطا به کانال ارورها"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(error, Exception):
        err_text = f"{type(error).__name__}: {error}"
        tb       = traceback.format_exc()[-500:]  # آخر ۵۰۰ کاراکتر
    else:
        err_text = str(error)
        tb       = ""

    text = (
        f"🚨 **خطا**\n\n"
        f"📍 منبع: `{source}`\n"
        f"❌ خطا: `{err_text}`\n"
        f"📅 زمان: `{now}`"
    )
    if detail:
        text += f"\n📝 جزئیات: {detail}"
    if tb:
        text += f"\n\n```\n{tb}\n```"

    await _send("errors_channel", text)


# ════════════════════════════════════════════════════════════════
#  کانال فروش / عملیات ادمین
# ════════════════════════════════════════════════════════════════
async def log_sale(admin_id: int, action: str, target_id: int, detail: str = "") -> None:
    """ثبت عملیات فروش/ادمین در کانال فروش"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    icons = {
        "sub_30":        "💎 اشتراک ۳۰ روزه",
        "sub_90":        "💎 اشتراک ۹۰ روزه",
        "sub_manual":    "💎 اشتراک دستی",
        "sub_revoke":    "❌ لغو اشتراک",
        "ban_user":      "🚫 مسدود کردن",
        "unban_user":    "✅ رفع مسدودیت",
        "add_admin":     "👑 افزودن ادمین",
        "remove_admin":  "❌ حذف ادمین",
        "add_seller":    "🛒 افزودن فروشنده",
        "remove_seller": "🗑 حذف فروشنده",
        "broadcast":     "📢 پیام همگانی",
        "msg_user":      "✉️ پیام به کاربر",
    }
    label = icons.get(action, f"⚙️ {action}")

    text = (
        f"{label}\n\n"
        f"👤 ادمین: `{admin_id}`\n"
        f"🎯 کاربر: `{target_id}`\n"
        f"📅 زمان: `{now}`"
    )
    if detail:
        text += f"\n📝 {detail}"

    await _send("sales_channel", text)
