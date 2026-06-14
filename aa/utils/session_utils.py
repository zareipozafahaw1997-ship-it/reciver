"""
utils/session_utils.py
مدیریت فایل‌های سشن
"""

import os
import shutil
from config import SESSIONS_DIR

DELETED_DIR = os.path.join(SESSIONS_DIR, "deleted")
os.makedirs(DELETED_DIR, exist_ok=True)


async def move_session_to_deleted(session_file: str) -> bool:
    """
    فایل سشن رو از sessions/ به sessions/deleted/ منتقل می‌کنه
    session_file: نام فایل مثلاً acc_123456.session
    """
    if not session_file:
        return False

    src = os.path.join(SESSIONS_DIR, session_file)
    if not os.path.exists(src):
        # شاید بدون پسوند ذخیره شده
        src_no_ext = os.path.join(SESSIONS_DIR, session_file.replace(".session", ""))
        if os.path.exists(src_no_ext + ".session"):
            src = src_no_ext + ".session"
        else:
            return False

    filename = os.path.basename(src)
    dst = os.path.join(DELETED_DIR, filename)

    # اگه قبلاً یه فایل با همین نام بود، پسوند اضافه کن
    if os.path.exists(dst):
        base, ext = os.path.splitext(filename)
        import time
        dst = os.path.join(DELETED_DIR, f"{base}_{int(time.time())}{ext}")

    try:
        shutil.move(src, dst)
        return True
    except Exception as e:
        print(f"⚠️ Session move error: {e}")
        return False
