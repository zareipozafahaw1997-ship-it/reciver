"""
utils/helpers.py
توابع کمکی async — چندزبانه
"""

from functools import wraps
from telethon import events, Button
from config import ADMIN_IDS
from database.mongo import MongoDB
from database.redis_client import RedisClient
from locales import t, DEFAULT_LANG


async def get_bot_name() -> str:
    from database.mongo import MongoDB as _DB
    return await _DB.get_bot_name()


# ════════════════════════════════════════════════════════════════
#  دریافت زبان کاربر (Redis → MongoDB → پیش‌فرض)
# ════════════════════════════════════════════════════════════════
async def get_user_lang(user_id: int) -> str:
    lang = await RedisClient.get_lang(user_id)
    if lang:
        return lang
    user = await MongoDB.get_user(user_id)
    if user and user.get("lang"):
        lang = user["lang"]
        await RedisClient.set_lang(user_id, lang)
        return lang
    return DEFAULT_LANG


# ════════════════════════════════════════════════════════════════
#  چک عضویت کانال اجباری
# ════════════════════════════════════════════════════════════════
async def _resolve_channel(client, channel: str):
    """
    هر فرمتی رو قبول می‌کنه:
    - @username
    - https://t.me/username
    - https://t.me/+inviteHash  (invite link)
    - -1001234567890 (آیدی عددی)
    """
    if not channel:
        return None
    ch = channel.strip()

    # آیدی عددی
    if ch.lstrip("-").isdigit():
        return int(ch)

    # لینک invite — https://t.me/+hash
    if "t.me/+" in ch or "t.me/joinchat" in ch:
        try:
            from telethon.tl.functions.messages import CheckChatInviteRequest
            # ربات نمی‌تونه invite link رو resolve کنه
            # باید آیدی عددی یا username استفاده بشه
            return None
        except Exception:
            return None

    # https://t.me/username یا @username
    if ch.startswith("https://t.me/"):
        ch = "@" + ch.replace("https://t.me/", "").split("/")[0].split("?")[0]
    if not ch.startswith("@"):
        ch = "@" + ch.lstrip("@")

    return ch


async def check_force_join(client, user_id: int) -> tuple[bool, str | None]:
    from database.mongo import MongoDB as _DB
    cfg = await _DB.get_force_join()
    if not cfg.get("enabled") or not cfg.get("channel"):
        return True, None

    channel_raw = cfg["channel"]
    entity = await _resolve_channel(client, channel_raw)

    # invite link — ربات نمی‌تونه چک کنه → bypass
    if entity is None:
        return True, None

    try:
        await client.get_permissions(entity, user_id)
        return True, None
    except Exception as e:
        err = str(e).lower()
        not_member = [
            "not_participant", "forbidden", "user_not",
            "getparticipantrequest", "participant", "not a member",
        ]
        if any(s in err for s in not_member):
            return False, channel_raw
        # خطای دیگه → bypass
        return True, None


def force_join_required(client):
    """دکوراتور factory — client رو می‌گیره"""
    def decorator(func):
        @wraps(func)
        async def wrapper(event, *args, **kwargs):
            uid = event.sender_id
            # ادمین‌ها bypass
            if uid in ADMIN_IDS or await MongoDB.is_admin(uid):
                return await func(event, *args, **kwargs)
            is_member, channel = await check_force_join(client, uid)
            if is_member:
                return await func(event, *args, **kwargs)
            lang = await get_user_lang(uid)
            ch_clean = channel.lstrip("@") if channel else ""
            msg = (
                "⚠️ **برای استفاده از ربات باید عضو کانال ما باشید!**"
                if lang == "fa" else
                "⚠️ **You must join our channel to use this bot!**"
                if lang == "en" else
                "⚠️ **您必须加入我们的频道才能使用此机器人！**"
            )
            buttons = [
                [Button.url("📢 عضویت در کانال" if lang == "fa" else
                            ("📢 Join Channel" if lang == "en" else "📢 加入频道"),
                            f"https://t.me/{ch_clean}")],
                [Button.inline("✅ عضو شدم" if lang == "fa" else
                               ("✅ I joined" if lang == "en" else "✅ 我已加入"),
                               data="check_join")],
            ]
            if hasattr(event, "edit"):
                await event.edit(msg, buttons=buttons)
            else:
                await event.respond(msg, buttons=buttons)
        return wrapper
    return decorator
def subscription_required(func):
    @wraps(func)
    async def wrapper(event, *args, **kwargs):
        uid = event.sender_id
        if uid in ADMIN_IDS or await MongoDB.is_admin(uid):
            return await func(event, *args, **kwargs)
        has_sub = await MongoDB.has_active_subscription(uid)
        if has_sub:
            return await func(event, *args, **kwargs)
        lang     = await get_user_lang(uid)
        sub_info = await MongoDB.get_subscription_info(uid)
        msg      = t(lang, "sub_expired_msg") if sub_info["expires_at"] else t(lang, "sub_required")
        buttons  = [
            [Button.inline(t(lang, "btn_support"), data="user_support")],
            [Button.inline(t(lang, "btn_back"),    data="user_home")],
        ]
        if hasattr(event, "edit"):
            await event.edit(msg, buttons=buttons)
        else:
            await event.respond(msg, buttons=buttons)
    return wrapper


# ════════════════════════════════════════════════════════════════
#  دکوراتور: فقط ادمین
# ════════════════════════════════════════════════════════════════
def admin_only(func):
    @wraps(func)
    async def wrapper(event, *args, **kwargs):
        uid = event.sender_id
        if uid in ADMIN_IDS or await MongoDB.is_admin(uid):
            return await func(event, *args, **kwargs)
        await event.answer("⛔ دسترسی ندارید!", alert=True)
    return wrapper


# ════════════════════════════════════════════════════════════════
#  دکوراتور: ادمین یا ادمین فروش
# ════════════════════════════════════════════════════════════════
def seller_or_admin(func):
    @wraps(func)
    async def wrapper(event, *args, **kwargs):
        uid = event.sender_id
        if uid in ADMIN_IDS or await MongoDB.is_admin(uid) or await MongoDB.is_seller(uid):
            return await func(event, *args, **kwargs)
        await event.answer("⛔ دسترسی ندارید!", alert=True)
    return wrapper


# ════════════════════════════════════════════════════════════════
#  دکوراتور: بررسی بن
# ════════════════════════════════════════════════════════════════
def ban_check(func):
    @wraps(func)
    async def wrapper(event, *args, **kwargs):
        uid = event.sender_id
        if await MongoDB.is_banned(uid):
            lang = await get_user_lang(uid)
            await event.answer(t(lang, "banned_msg"), alert=True)
            return
        return await func(event, *args, **kwargs)
    return wrapper


# ════════════════════════════════════════════════════════════════
#  دکوراتور: Rate Limit
# ════════════════════════════════════════════════════════════════
def rate_limit(action: str, max_calls: int = 5, window: int = 60):
    def decorator(func):
        @wraps(func)
        async def wrapper(event, *args, **kwargs):
            uid     = event.sender_id
            allowed = await RedisClient.check_rate_limit(uid, action, max_calls, window)
            if not allowed:
                lang = await get_user_lang(uid)
                await event.answer(t(lang, "rate_limit_msg", window=window), alert=True)
                return
            return await func(event, *args, **kwargs)
        return wrapper
    return decorator


# ════════════════════════════════════════════════════════════════
#  ثبت و دریافت کاربر (با کش Redis)
# ════════════════════════════════════════════════════════════════
async def get_or_register_user(event) -> dict | None:
    uid    = event.sender_id
    sender = await event.get_sender()
    await MongoDB.register_user(
        user_id=uid,
        username=getattr(sender, "username", None),
        full_name=f"{getattr(sender,'first_name','')} {getattr(sender,'last_name','')}".strip(),
    )
    cached = await RedisClient.get_cached_user(uid)
    if cached:
        return cached
    user = await MongoDB.get_user(uid)
    if user:
        await RedisClient.cache_user(uid, user)
        await RedisClient.set_online(uid)
    return user


# ════════════════════════════════════════════════════════════════
#  فرمت‌دهی پروفایل کاربر (پنل ادمین — همیشه فارسی)
# ════════════════════════════════════════════════════════════════
def fmt_user(user: dict) -> str:
    from datetime import datetime, timezone
    name   = user.get("full_name", "نامشخص")
    uid    = user.get("user_id", "؟")
    uname  = f"@{user['username']}" if user.get("username") else "ندارد"
    banned = "🚫 بله" if user.get("is_banned") else "✅ خیر"
    if user.get("is_admin"):
        role = "👑 ادمین"
    elif user.get("is_seller"):
        role = "🛒 ادمین فروش"
    else:
        role = "👤 کاربر"
    exp    = user.get("sub_expires_at")
    if exp:
        now = datetime.now(timezone.utc)
        if isinstance(exp, str):
            from dateutil.parser import parse
            exp = parse(exp)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        sub_status = f"✅ فعال ({max(0,(exp-now).days)} روز)" if exp > now else "⏰ منقضی"
    else:
        sub_status = "❌ ندارد"
    return (
        f"👤 **{name}**\n"
        f"🆔 `{uid}`\n"
        f"📛 یوزرنیم: {uname}\n"
        f"🚫 بن: {banned}\n"
        f"🎭 نقش: {role}\n"
        f"💎 اشتراک: {sub_status}"
    )
