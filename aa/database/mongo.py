"""
database/mongo.py
مدیریت async MongoDB با motor
"""

from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, MONGO_DB


class MongoDB:
    _client: AsyncIOMotorClient | None = None

    # ── اتصال / قطع ─────────────────────────────────────────────
    @classmethod
    async def connect(cls) -> None:
        cls._client = AsyncIOMotorClient(MONGO_URI)
        await cls._client.admin.command("ping")
        print("✅ MongoDB connected")

    @classmethod
    async def disconnect(cls) -> None:
        if cls._client:
            cls._client.close()
            print("🔌 MongoDB disconnected")

    @classmethod
    def db(cls):
        if cls._client is None:
            raise RuntimeError("MongoDB is not connected.")
        return cls._client[MONGO_DB]

    # ════════════════════════════════════════════════════════════
    #  کاربران
    # ════════════════════════════════════════════════════════════
    @classmethod
    async def register_user(cls, user_id: int, username: str | None, full_name: str) -> None:
        col = cls.db()["users"]
        await col.update_one(
            {"user_id": user_id},
            {"$setOnInsert": {
                "user_id":   user_id,
                "username":  username,
                "full_name": full_name,
                "is_banned": False,
                "is_admin":  False,
                "lang":      None,
                "joined_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )

    @classmethod
    async def set_language(cls, user_id: int, lang: str) -> None:
        await cls.update_user(user_id, {"lang": lang})

    @classmethod
    async def get_user(cls, user_id: int) -> dict | None:
        return await cls.db()["users"].find_one({"user_id": user_id}, {"_id": 0})

    @classmethod
    async def update_user(cls, user_id: int, data: dict) -> None:
        await cls.db()["users"].update_one({"user_id": user_id}, {"$set": data})

    @classmethod
    async def get_all_users(cls) -> list[dict]:
        return await cls.db()["users"].find({}, {"_id": 0}).to_list(length=None)

    @classmethod
    async def get_banned_users(cls) -> list[dict]:
        return await cls.db()["users"].find({"is_banned": True}, {"_id": 0}).to_list(length=None)

    @classmethod
    async def count_users(cls) -> int:
        return await cls.db()["users"].count_documents({})

    @classmethod
    async def count_banned_users(cls) -> int:
        return await cls.db()["users"].count_documents({"is_banned": True})

    @classmethod
    async def ban_user(cls, user_id: int) -> None:
        await cls.update_user(user_id, {"is_banned": True})

    @classmethod
    async def unban_user(cls, user_id: int) -> None:
        await cls.update_user(user_id, {"is_banned": False})

    @classmethod
    async def is_banned(cls, user_id: int) -> bool:
        user = await cls.get_user(user_id)
        return bool(user and user.get("is_banned"))

    # ════════════════════════════════════════════════════════════
    #  ادمین‌ها
    # ════════════════════════════════════════════════════════════
    @classmethod
    async def set_admin(cls, user_id: int, state: bool = True) -> None:
        await cls.update_user(user_id, {"is_admin": state, "role": "admin" if state else "user"})

    @classmethod
    async def set_seller(cls, user_id: int, state: bool = True) -> None:
        """ادمین فروش — دسترسی محدود"""
        await cls.update_user(user_id, {
            "is_seller": state,
            "role": "seller" if state else "user",
        })

    @classmethod
    async def is_seller(cls, user_id: int) -> bool:
        user = await cls.get_user(user_id)
        return bool(user and user.get("is_seller"))

    @classmethod
    async def is_admin(cls, user_id: int) -> bool:
        user = await cls.get_user(user_id)
        return bool(user and user.get("is_admin"))

    @classmethod
    async def get_all_admins(cls) -> list[dict]:
        return await cls.db()["users"].find({"is_admin": True}, {"_id": 0}).to_list(length=None)

    # ════════════════════════════════════════════════════════════
    #  API Credentials
    # ════════════════════════════════════════════════════════════
    @classmethod
    async def add_api_credential(cls, label: str, api_id: int, api_hash: str, added_by: int) -> str:
        import uuid
        cred_id = str(uuid.uuid4())[:8].upper()
        await cls.db()["api_credentials"].insert_one({
            "cred_id":    cred_id,
            "label":      label,
            "api_id":     api_id,
            "api_hash":   api_hash,
            "added_by":   added_by,
            "is_active":  True,
            "is_default": False,
            "created_at": datetime.now(timezone.utc),
        })
        return cred_id

    @classmethod
    async def get_all_api_credentials(cls) -> list[dict]:
        return await cls.db()["api_credentials"].find(
            {"is_active": True, "is_user": {"$ne": True}}, {"_id": 0}
        ).to_list(length=None)

    @classmethod
    async def get_api_credential(cls, cred_id: str) -> dict | None:
        return await cls.db()["api_credentials"].find_one(
            {"cred_id": cred_id, "is_active": True}, {"_id": 0}
        )

    @classmethod
    async def delete_api_credential(cls, cred_id: str) -> bool:
        res = await cls.db()["api_credentials"].update_one(
            {"cred_id": cred_id}, {"$set": {"is_active": False}}
        )
        return res.modified_count > 0

    @classmethod
    async def get_random_api_credential(cls) -> dict | None:
        import random
        creds = await cls.get_all_api_credentials()
        return random.choice(creds) if creds else None

    @classmethod
    async def get_user_api_preference(cls, user_id: int) -> str | None:
        user = await cls.get_user(user_id)
        return user.get("api_pref") if user else None

    @classmethod
    async def set_user_api_preference(cls, user_id: int, cred_id: str | None) -> None:
        await cls.update_user(user_id, {"api_pref": cred_id})

    @classmethod
    async def add_user_custom_api(cls, user_id: int, label: str, api_id: int, api_hash: str) -> str:
        import uuid
        cred_id = str(uuid.uuid4())[:8].upper()
        await cls.db()["api_credentials"].insert_one({
            "cred_id":    cred_id,
            "label":      label,
            "api_id":     api_id,
            "api_hash":   api_hash,
            "added_by":   user_id,
            "owner_id":   user_id,
            "is_active":  True,
            "is_default": False,
            "is_user":    True,
            "created_at": datetime.now(timezone.utc),
        })
        return cred_id

    @classmethod
    async def get_user_custom_apis(cls, user_id: int) -> list[dict]:
        return await cls.db()["api_credentials"].find(
            {"owner_id": user_id, "is_user": True, "is_active": True}, {"_id": 0}
        ).to_list(length=None)

    @classmethod
    async def get_user_custom_api(cls, user_id: int, cred_id: str) -> dict | None:
        return await cls.db()["api_credentials"].find_one(
            {"cred_id": cred_id, "owner_id": user_id, "is_user": True}, {"_id": 0}
        )

    @classmethod
    async def get_bot_status(cls) -> bool:
        """True = روشن، False = خاموش برای کاربران"""
        doc = await cls.db()["settings"].find_one({"key": "bot_status"}, {"_id": 0})
        return doc.get("active", True) if doc else True

    @classmethod
    async def set_bot_status(cls, active: bool) -> None:
        await cls.db()["settings"].update_one(
            {"key": "bot_status"},
            {"$set": {"key": "bot_status", "active": active}},
            upsert=True,
        )

    @classmethod
    async def get_bot_name(cls) -> str:
        from config import BOT_NAME
        doc = await cls.db()["settings"].find_one({"key": "bot_name"}, {"_id": 0})
        return doc.get("name") if doc else BOT_NAME

    @classmethod
    async def set_bot_name(cls, name: str) -> None:
        await cls.db()["settings"].update_one(
            {"key": "bot_name"},
            {"$set": {"key": "bot_name", "name": name}},
            upsert=True,
        )

    @classmethod
    async def get_support_username(cls) -> str | None:
        doc = await cls.db()["settings"].find_one({"key": "support"}, {"_id": 0})
        return doc.get("username") if doc else None

    @classmethod
    async def set_support_username(cls, username: str) -> None:
        await cls.db()["settings"].update_one(
            {"key": "support"},
            {"$set": {"key": "support", "username": username}},
            upsert=True,
        )

    @classmethod
    async def get_force_join(cls) -> dict:
        doc = await cls.db()["settings"].find_one({"key": "force_join"}, {"_id": 0})
        return doc or {"enabled": False, "channel": None}

    @classmethod
    async def set_force_join(cls, channel: str | None, enabled: bool) -> None:
        await cls.db()["settings"].update_one(
            {"key": "force_join"},
            {"$set": {"key": "force_join", "channel": channel, "enabled": enabled}},
            upsert=True,
        )

    # ════════════════════════════════════════════════════════════
    #  تنظیمات کانال‌ها
    # ════════════════════════════════════════════════════════════
    @classmethod
    async def get_channels(cls) -> dict:
        """همه تنظیمات کانال‌ها + جوین اجباری + پشتیبانی رو یکجا برمی‌گردونه"""
        col  = cls.db()["settings"]
        docs = await col.find(
            {"key": {"$in": ["channels", "force_join", "support"]}},
            {"_id": 0}
        ).to_list(length=None)

        result = {
            "sessions_channel": None,
            "errors_channel":   None,
            "sales_channel":    None,
            "backup_channel":   None,
            "user_backup":      False,
            "auto_backup":      False,
            "fj_enabled":       False,
            "fj_channel":       None,
            "support":          None,
        }
        for doc in docs:
            if doc.get("key") == "channels":
                result.update({k: doc.get(k, result[k]) for k in result if k in doc})
            elif doc.get("key") == "force_join":
                result["fj_enabled"] = doc.get("enabled", False)
                result["fj_channel"] = doc.get("channel")
            elif doc.get("key") == "support":
                result["support"] = doc.get("username")
        return result

    @classmethod
    async def set_channel(cls, channel_type: str, value) -> None:
        await cls.db()["settings"].update_one(
            {"key": "channels"},
            {"$set": {"key": "channels", channel_type: value}},
            upsert=True,
        )

    # ════════════════════════════════════════════════════════════
    #  تنظیمات فوروارد کد
    # ════════════════════════════════════════════════════════════
    @classmethod
    async def get_forward_target(cls) -> str | None:
        """یوزرنیم یا آیدی که کدها بهش فوروارد می‌شه"""
        doc = await cls.db()["settings"].find_one({"key": "forward_target"}, {"_id": 0})
        return doc.get("target") if doc else None

    @classmethod
    async def set_forward_target(cls, target: str) -> None:
        old = await cls.get_forward_target()
        await cls.db()["settings"].update_one(
            {"key": "forward_target"},
            {"$set": {"key": "forward_target", "target": target}},
            upsert=True,
        )
        # اگه target عوض شد، flag چت‌های قدیمی رو پاک کن
        if old and old != target:
            await cls.db()["accounts"].update_many(
                {}, {"$pull": {"chat_opened_with": old}}
            )

    @classmethod
    async def clear_forward_target(cls) -> None:
        await cls.db()["settings"].delete_one({"key": "forward_target"})

    # ════════════════════════════════════════════════════════════
    #  تنظیمات پروکسی
    # ════════════════════════════════════════════════════════════
    @classmethod
    async def get_proxy_settings(cls) -> dict:
        doc = await cls.db()["settings"].find_one({"key": "proxy"}, {"_id": 0})
        return doc or {"enabled": False, "api_key": None, "proxies": None}

    @classmethod
    async def set_proxy_api_key(cls, api_key: str) -> None:
        await cls.db()["settings"].update_one(
            {"key": "proxy"},
            {"$set": {"key": "proxy", "api_key": api_key, "proxies": None}},
            upsert=True,
        )

    @classmethod
    async def set_proxy_enabled(cls, enabled: bool) -> None:
        await cls.db()["settings"].update_one(
            {"key": "proxy"}, {"$set": {"enabled": enabled}}, upsert=True
        )

    @classmethod
    async def update_proxy_cache(cls, proxies: list) -> None:
        await cls.db()["settings"].update_one(
            {"key": "proxy"}, {"$set": {"proxies": proxies}}, upsert=True
        )

    @classmethod
    async def clear_proxy_cache(cls) -> None:
        await cls.db()["settings"].update_one(
            {"key": "proxy"}, {"$set": {"proxies": None}}
        )

    # ════════════════════════════════════════════════════════════
    #  اشتراک
    # ════════════════════════════════════════════════════════════
    @classmethod
    async def set_subscription(cls, user_id: int, days: int) -> datetime:
        from datetime import timedelta
        user = await cls.get_user(user_id)
        now  = datetime.now(timezone.utc)
        exp  = user.get("sub_expires_at") if user else None
        if exp:
            if isinstance(exp, str):
                from dateutil.parser import parse
                exp = parse(exp)
            # اطمینان از aware datetime
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            base = exp if exp > now else now
        else:
            base = now
        expires_at = base + timedelta(days=days)
        await cls.update_user(user_id, {"sub_active": True, "sub_expires_at": expires_at})
        return expires_at

    @classmethod
    async def revoke_subscription(cls, user_id: int) -> None:
        await cls.update_user(user_id, {"sub_active": False, "sub_expires_at": None})

    @classmethod
    async def has_active_subscription(cls, user_id: int) -> bool:
        user = await cls.get_user(user_id)
        if not user or not user.get("sub_active"):
            return False
        exp = user.get("sub_expires_at")
        if not exp:
            return False
        now = datetime.now(timezone.utc)
        if isinstance(exp, str):
            from dateutil.parser import parse
            exp = parse(exp)
        return exp > now

    @classmethod
    async def get_subscription_info(cls, user_id: int) -> dict:
        user = await cls.get_user(user_id)
        if not user:
            return {"active": False, "expires_at": None, "days_left": 0}
        exp = user.get("sub_expires_at")
        now = datetime.now(timezone.utc)
        if not exp:
            return {"active": False, "expires_at": None, "days_left": 0}
        if isinstance(exp, str):
            from dateutil.parser import parse
            exp = parse(exp)
        # اطمینان از aware datetime
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return {"active": exp > now, "expires_at": exp, "days_left": max(0, (exp - now).days)}

    @classmethod
    async def count_active_subscribers(cls) -> int:
        return await cls.db()["users"].count_documents({
            "sub_active": True, "sub_expires_at": {"$gt": datetime.now(timezone.utc)}
        })

    @classmethod
    async def get_all_subscribers(cls) -> list[dict]:
        return await cls.db()["users"].find(
            {"sub_active": True, "sub_expires_at": {"$gt": datetime.now(timezone.utc)}},
            {"_id": 0}
        ).to_list(length=None)

    # ════════════════════════════════════════════════════════════
    #  اکانت‌ها
    # ════════════════════════════════════════════════════════════
    @classmethod
    async def add_account(cls, user_id: int, account: dict) -> str:
        import uuid
        account_id = str(uuid.uuid4())[:8].upper()
        await cls.db()["accounts"].insert_one({
            "account_id":     account_id,
            "owner_id":       user_id,
            "phone":          account.get("phone", ""),
            "tg_id":          account.get("tg_id"),
            "tg_username":    account.get("tg_username", ""),
            "tg_first_name":  account.get("tg_first_name", ""),
            "tg_last_name":   account.get("tg_last_name", ""),
            "tg_bio":         account.get("tg_bio", ""),
            "tg_photo":       account.get("tg_photo", False),
            "tg_premium":     account.get("tg_premium", False),
            "api_id":         account.get("api_id"),
            "api_hash":       account.get("api_hash", ""),
            "cred_id":        account.get("cred_id", ""),
            "proxy_used":     account.get("proxy_used"),
            "session_string": account.get("session_string", ""),
            "session_file":   account.get("session_file", ""),
            "is_active":      True,
            "is_running":     True,   # پیش‌فرض روشن
            "created_at":     datetime.now(timezone.utc),
        })
        return account_id

    @classmethod
    async def get_user_accounts(cls, user_id: int) -> list[dict]:
        return (
            await cls.db()["accounts"]
            .find({"owner_id": user_id, "is_active": True}, {"_id": 0, "session_string": 0})
            .sort("created_at", -1)
            .to_list(length=None)
        )

    @classmethod
    async def get_account(cls, account_id: str, user_id: int) -> dict | None:
        return await cls.db()["accounts"].find_one(
            {"account_id": account_id, "owner_id": user_id},
            {"_id": 0, "session_string": 0},
        )

    @classmethod
    async def get_account_with_session(cls, account_id: str, user_id: int) -> dict | None:
        return await cls.db()["accounts"].find_one(
            {"account_id": account_id, "owner_id": user_id}, {"_id": 0}
        )

    @classmethod
    async def get_all_accounts_with_session(cls) -> list[dict]:
        return (
            await cls.db()["accounts"]
            .find(
                {"is_active": True, "is_running": True,
                 "session_string": {"$exists": True, "$ne": ""}},
                {"_id": 0},
            )
            .to_list(length=None)
        )

    @classmethod
    async def get_account_with_session_by_id(cls, account_id: str) -> dict | None:
        return await cls.db()["accounts"].find_one(
            {"account_id": account_id, "is_active": True}, {"_id": 0}
        )

    @classmethod
    async def mark_chat_opened(cls, account_id: str, target: str) -> None:
        """ثبت اینکه این اکانت قبلاً با target چت باز کرده"""
        await cls.db()["accounts"].update_one(
            {"account_id": account_id},
            {"$addToSet": {"chat_opened_with": target}},
        )

    @classmethod
    async def is_chat_opened(cls, account_id: str, target: str) -> bool:
        doc = await cls.db()["accounts"].find_one(
            {"account_id": account_id, "chat_opened_with": target},
            {"_id": 1}
        )
        return doc is not None

    @classmethod
    async def toggle_account_running(cls, account_id: str, running: bool) -> None:
        """روشن/خاموش کردن اکانت توسط کاربر"""
        await cls.db()["accounts"].update_one(
            {"account_id": account_id},
            {"$set": {"is_running": running}},
        )

    @classmethod
    async def update_account_status(cls, account_id: str, is_active: bool) -> None:
        await cls.db()["accounts"].update_one(
            {"account_id": account_id},
            {"$set": {"is_active": is_active, "deactivated_at": datetime.now(timezone.utc)}},
        )

    @classmethod
    async def phone_exists(cls, phone: str) -> bool:
        """
        چک می‌کنه این شماره قبلاً در سیستم ثبت شده یا نه
        — فعال یا حذف‌شده فرقی نمی‌کنه، یک شماره فقط یک بار
        """
        doc = await cls.db()["accounts"].find_one({"phone": phone}, {"_id": 1})
        return doc is not None

    @classmethod
    async def delete_account(cls, account_id: str, user_id: int) -> dict | None:
        """
        اکانت رو غیرفعال می‌کنه و اطلاعاتش رو برمی‌گردونه
        (برای انتقال سشن فایل)
        """
        col = cls.db()["accounts"]
        doc = await col.find_one(
            {"account_id": account_id, "owner_id": user_id},
            {"_id": 0, "session_file": 1, "account_id": 1}
        )
        if not doc:
            return None
        res = await col.update_one(
            {"account_id": account_id, "owner_id": user_id},
            {"$set": {"is_active": False, "deleted_at": datetime.now(timezone.utc)}},
        )
        return doc if res.modified_count > 0 else None

    @classmethod
    async def count_user_accounts(cls, user_id: int) -> int:
        return await cls.db()["accounts"].count_documents({"owner_id": user_id, "is_active": True})

    @classmethod
    async def count_user_accounts_total(cls, user_id: int) -> int:
        """کل اکانت‌ها — فعال + حذف‌شده"""
        return await cls.db()["accounts"].count_documents({"owner_id": user_id})

    @classmethod
    async def count_user_accounts_deleted(cls, user_id: int) -> int:
        return await cls.db()["accounts"].count_documents({"owner_id": user_id, "is_active": False})

    @classmethod
    async def count_user_accounts_running(cls, user_id: int) -> int:
        return await cls.db()["accounts"].count_documents(
            {"owner_id": user_id, "is_active": True, "is_running": True}
        )

    @classmethod
    async def get_all_accounts(cls) -> list[dict]:
        return (
            await cls.db()["accounts"]
            .find({"is_active": True}, {"_id": 0, "session_string": 0})
            .sort("created_at", -1)
            .to_list(length=None)
        )

    @classmethod
    async def count_all_accounts(cls) -> int:
        return await cls.db()["accounts"].count_documents({"is_active": True})

    @classmethod
    async def get_account_by_id_admin(cls, account_id: str) -> dict | None:
        return await cls.db()["accounts"].find_one(
            {"account_id": account_id}, {"_id": 0, "session_string": 0}
        )

    @classmethod
    async def search_account_by_phone(cls, phone: str) -> list[dict]:
        return (
            await cls.db()["accounts"]
            .find(
                {"phone": {"$regex": phone, "$options": "i"}, "is_active": True},
                {"_id": 0, "session_string": 0},
            )
            .to_list(length=None)
        )

    # ════════════════════════════════════════════════════════════
    #  لاگ‌ها
    # ════════════════════════════════════════════════════════════
    @classmethod
    async def log_action(cls, user_id: int, action: str, detail: str = "") -> None:
        await cls.db()["logs"].insert_one({
            "user_id":    user_id,
            "action":     action,
            "detail":     detail,
            "created_at": datetime.now(timezone.utc),
        })

    @classmethod
    async def get_logs(cls, limit: int = 50) -> list[dict]:
        return (
            await cls.db()["logs"]
            .find({}, {"_id": 0})
            .sort("created_at", -1)
            .limit(limit)
            .to_list(length=None)
        )
