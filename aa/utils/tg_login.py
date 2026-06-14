"""
utils/tg_login.py
مدیریت async لاگین کلاینت تلگرام
- API credential: از دیتابیس (رندوم یا انتخاب کاربر)
- Proxy: از Webshare (اگه فعال باشه)
"""

import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    PhoneNumberInvalidError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    SessionPasswordNeededError,
    PasswordHashInvalidError,
    FloodWaitError,
)
from config import API_ID, API_HASH, SESSIONS_DIR
from utils.proxy_manager import get_random_proxy

os.makedirs(SESSIONS_DIR, exist_ok=True)


async def _resolve_api_credential(cred_id: str | None) -> tuple[int, str, str]:
    """
    برمی‌گردونه (api_id, api_hash, cred_id)
    اگه cred_id داده شده → از دیتابیس بخون
    اگه نه → رندوم از دیتابیس
    اگه دیتابیس خالیه → از config پیش‌فرض
    """
    from database.mongo import MongoDB
    if cred_id:
        cred = await MongoDB.get_api_credential(cred_id)
        if cred:
            return cred["api_id"], cred["api_hash"], cred["cred_id"]

    # رندوم از دیتابیس
    cred = await MongoDB.get_random_api_credential()
    if cred:
        return cred["api_id"], cred["api_hash"], cred["cred_id"]

    # fallback به config
    return API_ID, API_HASH, "default"


class LoginSession:
    """نگه‌داری وضعیت لاگین یک کاربر در حین احراز هویت"""

    _active: dict[int, "LoginSession"] = {}

    def __init__(self, user_id: int):
        self.user_id:          int = user_id
        self.client:           TelegramClient | None = None
        self.phone:            str = ""
        self.phone_code_hash:  str = ""
        self.api_id:           int = 0
        self.api_hash:         str = ""
        self.cred_id:          str = ""
        self.proxy_used:       dict | None = None

    @classmethod
    def get(cls, user_id: int) -> "LoginSession | None":
        return cls._active.get(user_id)

    @classmethod
    def create(cls, user_id: int) -> "LoginSession":
        obj = cls(user_id)
        cls._active[user_id] = obj
        return obj

    @classmethod
    async def destroy(cls, user_id: int) -> None:
        obj = cls._active.pop(user_id, None)
        if obj and obj.client:
            try:
                await obj.client.disconnect()
            except Exception:
                pass

    # ════════════════════════════════════════════════════════════
    #  مرحله ۱ — ارسال کد
    # ════════════════════════════════════════════════════════════
    async def send_code(self, phone: str, cred_id: str | None = None) -> dict:
        self.phone = phone

        # دریافت API credential
        self.api_id, self.api_hash, self.cred_id = await _resolve_api_credential(cred_id)

        # دریافت پروکسی تازه از Webshare
        proxy = await get_random_proxy()
        self.proxy_used = None

        kwargs = {}
        if proxy:
            self.proxy_used = {
                "host":     proxy["addr"],
                "port":     proxy["port"],
                "username": proxy["username"],
            }
            kwargs["proxy"] = (
                proxy["proxy_type"],
                proxy["addr"],
                proxy["port"],
                True,
                proxy["username"],
                proxy["password"],
            )

        self.client = TelegramClient(
            StringSession(),
            self.api_id,
            self.api_hash,
            **kwargs,
        )

        try:
            await self.client.connect()
            result = await self.client.send_code_request(phone)
            self.phone_code_hash = result.phone_code_hash
            return {"ok": True}

        except PhoneNumberInvalidError:
            await self.client.disconnect()
            return {"ok": False, "error": "📵 شماره تلفن نامعتبر است."}

        except FloodWaitError as e:
            await self.client.disconnect()
            return {"ok": False, "error": f"⏳ تلگرام بلاک کرد. {e.seconds} ثانیه صبر کنید."}

        except Exception as e:
            await self.client.disconnect()
            return {"ok": False, "error": f"❌ خطا: {e}"}

    # ════════════════════════════════════════════════════════════
    #  مرحله ۲ — تأیید کد
    # ════════════════════════════════════════════════════════════
    async def verify_code(self, code: str) -> dict:
        if not self.client or not self.client.is_connected():
            return {"ok": False, "error": "⚠️ سشن منقضی شده. دوباره شروع کنید."}
        try:
            await self.client.sign_in(
                phone=self.phone,
                code=code,
                phone_code_hash=self.phone_code_hash,
            )
            return await self._finalize()
        except SessionPasswordNeededError:
            return {"ok": True, "need_password": True}
        except PhoneCodeInvalidError:
            return {"ok": False, "error": "❌ کد اشتباه است."}
        except PhoneCodeExpiredError:
            return {"ok": False, "error": "⌛ کد منقضی شده. دوباره /start بزنید."}
        except Exception as e:
            return {"ok": False, "error": f"❌ خطا: {e}"}

    # ════════════════════════════════════════════════════════════
    #  مرحله ۳ — تأیید پسورد 2FA
    # ════════════════════════════════════════════════════════════
    async def verify_password(self, password: str) -> dict:
        if not self.client or not self.client.is_connected():
            return {"ok": False, "error": "⚠️ سشن منقضی شده. دوباره شروع کنید."}
        try:
            await self.client.sign_in(password=password)
            return await self._finalize()
        except PasswordHashInvalidError:
            return {"ok": False, "error": "🔐 پسورد اشتباه است."}
        except Exception as e:
            return {"ok": False, "error": f"❌ خطا: {e}"}

    # ════════════════════════════════════════════════════════════
    #  نهایی‌سازی — دریافت اطلاعات کامل اکانت
    # ════════════════════════════════════════════════════════════
    async def _finalize(self) -> dict:
        try:
            me = await self.client.get_me()

            # اطلاعات کامل‌تر
            bio = ""
            try:
                full = await self.client(
                    __import__("telethon.tl.functions.users", fromlist=["GetFullUserRequest"])
                    .GetFullUserRequest(me)
                )
                bio = full.full_user.about or ""
            except Exception:
                pass

            session_string   = self.client.session.save()
            session_filename = f"acc_{me.id}"
            session_file_path = os.path.join(SESSIONS_DIR, session_filename)

            # ذخیره فایل .session
            file_client = TelegramClient(session_file_path, self.api_id, self.api_hash)
            await file_client.connect()
            try:
                await file_client.session.set_dc(
                    self.client.session.dc_id,
                    self.client.session.server_address,
                    self.client.session.port,
                )
                file_client.session.auth_key = self.client.session.auth_key
                file_client.session.save()
            except Exception:
                pass
            await file_client.disconnect()

            account_info = {
                "phone":          self.phone,
                "tg_id":          me.id,
                "tg_username":    me.username or "",
                "tg_first_name":  me.first_name or "",
                "tg_last_name":   me.last_name or "",
                "tg_bio":         bio,
                "tg_photo":       bool(me.photo),
                "tg_premium":     bool(getattr(me, "premium", False)),
                # API که استفاده شد
                "api_id":         self.api_id,
                "api_hash":       self.api_hash,
                "cred_id":        self.cred_id,
                # پروکسی که استفاده شد
                "proxy_used":     self.proxy_used,
                # سشن
                "session_string": session_string,
                "session_file":   f"{session_filename}.session",
            }

            await self.client.disconnect()
            return {"ok": True, "need_password": False, "account": account_info}

        except Exception as e:
            return {"ok": False, "error": f"❌ خطا در دریافت اطلاعات: {e}"}
