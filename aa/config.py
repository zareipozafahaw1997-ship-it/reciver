"""
config.py
تنظیمات مرکزی پروژه
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── Telegram ───────────────────────────────────────────────────
API_ID    = int(os.getenv("API_ID", "0"))
API_HASH  = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ─── Admins ─────────────────────────────────────────────────────
ADMIN_IDS: list[int] = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]

# ─── MongoDB ────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB", "engineering_bot")

# ─── Redis ──────────────────────────────────────────────────────
REDIS_HOST     = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT     = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_DB       = int(os.getenv("REDIS_DB", "0"))

# ─── Cache TTL (ثانیه) ──────────────────────────────────────────
CACHE_TTL_USER  = 300   # 5 دقیقه
CACHE_TTL_SHORT = 60    # 1 دقیقه

# ─── Sessions ───────────────────────────────────────────────────
SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "sessions")

# ─── Bot Info ───────────────────────────────────────────────────
BOT_NAME    = "🤖 Zlogin"
BOT_VERSION = "1.0.0"
