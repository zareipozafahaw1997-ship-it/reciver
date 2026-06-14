"""
سرویس دریافت کد تلگرام از سشن اکانت
سشن رو آنلاین نگه می‌داره و منتظر کد جدید از 777000 می‌مونه
"""
import re
import logging
import asyncio
from pathlib import Path
from typing import Optional
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from src.config import Config

logger = logging.getLogger(__name__)

# آیدی تلگرام که کدها رو می‌فرسته
TELEGRAM_SENDER_ID = 777000


def _extract_code_from_text(text: str) -> Optional[str]:
    """استخراج کد تایید از متن پیام تلگرام"""
    if not text:
        return None

    patterns = [
        r'[Ll]ogin\s+code[:\s]+(\d{4,8})',   # Login code: 12345
        r'[Cc]ode[:\s]+(\d{4,8})',             # code: 12345
        r'کد[:\s]+(\d{4,8})',                   # کد: 12345
        r'(\d{4,8})\s+is your',                # 12345 is your code
        r'(?<!\d)(\d{5})(?!\d)',               # دقیقاً 5 رقم مستقل
        r'(?<!\d)(\d{4,8})(?!\d)',             # 4 تا 8 رقم مستقل
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    return None


async def get_code_from_session(session_path: str, timeout: int = 120, cancel_flag: Optional[dict] = None) -> dict:
    """
    سشن رو آنلاین می‌کنه و منتظر کد جدید از 777000 می‌مونه.

    Args:
        session_path: مسیر فایل سشن
        timeout: حداکثر زمان انتظار (ثانیه)
        cancel_flag: دیکشنری {'cancelled': False} برای لغو از بیرون

    Returns:
        {'success': bool, 'code': str|None, 'message': str, 'msg_preview': str}
    """
    client = None
    try:
        session_file = Path(session_path)
        if not session_file.exists():
            return {
                'success': False, 'code': None,
                'message': 'فایل سشن پیدا نشد', 'msg_preview': ''
            }

        session_string = session_file.read_text(encoding='utf-8')

        client = TelegramClient(
            StringSession(session_string),
            Config.API_ID,
            Config.API_HASH
        )

        await client.connect()

        if not await client.is_user_authorized():
            await client.disconnect()
            return {
                'success': False, 'code': None,
                'message': 'سشن نامعتبر است', 'msg_preview': ''
            }

        logger.info(f"سشن آنلاین شد، منتظر کد از 777000 (timeout={timeout}s)...")

        code_future: asyncio.Future = asyncio.get_event_loop().create_future()

        @client.on(events.NewMessage(from_users=TELEGRAM_SENDER_ID))
        async def on_new_message(event):
            if code_future.done():
                return
            msg_text = event.raw_text or ''
            code = _extract_code_from_text(msg_text)
            if code:
                logger.info(f"کد جدید دریافت شد: {code}")
                code_future.set_result({
                    'success': True,
                    'code': code,
                    'message': 'کد جدید دریافت شد',
                    'msg_preview': msg_text[:100]
                })

        await client.catch_up()

        # polling با بررسی cancel_flag هر ثانیه
        elapsed = 0
        while elapsed < timeout:
            if cancel_flag and cancel_flag.get('cancelled'):
                return {
                    'success': False, 'code': None,
                    'message': 'عملیات توسط کاربر لغو شد', 'msg_preview': ''
                }
            if code_future.done():
                return code_future.result()
            await asyncio.sleep(1)
            elapsed += 1

        return {
            'success': False, 'code': None,
            'message': f'کدی در {timeout} ثانیه دریافت نشد',
            'msg_preview': ''
        }

    except Exception as e:
        logger.exception(f"خطا در دریافت کد: {e}")
        return {
            'success': False, 'code': None,
            'message': f'خطا: {str(e)}', 'msg_preview': ''
        }

    finally:
        if client and client.is_connected():
            try:
                await client.disconnect()
            except Exception:
                pass
