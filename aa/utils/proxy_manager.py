"""
utils/proxy_manager.py
مدیریت async پروکسی از Webshare.io
API: GET https://proxy.webshare.io/api/v2/proxy/list/
Auth: Authorization: Token <API_KEY>
"""

import random
import aiohttp
from database.mongo import MongoDB


WEBSHARE_API = "https://proxy.webshare.io/api/v2/proxy/list/"


# ════════════════════════════════════════════════════════════════
#  دریافت تنظیمات پروکسی از دیتابیس
# ════════════════════════════════════════════════════════════════
async def get_proxy_config() -> dict:
    """
    برمی‌گردونه:
    {
        "enabled": bool,
        "api_key": str | None,
        "proxies": [...] | None   ← کش شده
    }
    """
    return await MongoDB.get_proxy_settings()


async def is_proxy_enabled() -> bool:
    cfg = await get_proxy_config()
    return bool(cfg and cfg.get("enabled") and cfg.get("api_key"))


# ════════════════════════════════════════════════════════════════
#  دریافت لیست پروکسی از Webshare
# ════════════════════════════════════════════════════════════════
async def fetch_proxies_from_webshare(api_key: str) -> list[dict]:
    """
    لیست پروکسی‌ها رو از Webshare می‌گیره.
    هر آیتم: {"host": ..., "port": ..., "username": ..., "password": ...}
    """
    proxies = []
    url     = WEBSHARE_API
    headers = {"Authorization": f"Token {api_key}"}
    params  = {"mode": "direct", "page": 1, "page_size": 100}

    async with aiohttp.ClientSession() as session:
        while url:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    raise Exception(f"Webshare API error: {resp.status} — {await resp.text()}")
                data = await resp.json()

            for p in data.get("results", []):
                proxies.append({
                    "host":     p["proxy_address"],
                    "port":     p["port"],
                    "username": p["username"],
                    "password": p["password"],
                })

            # صفحه بعدی
            url    = data.get("next")
            params = {}   # next URL کامله، params دیگه لازم نیست

    return proxies


# ════════════════════════════════════════════════════════════════
#  تست اتصال یک پروکسی
# ════════════════════════════════════════════════════════════════
async def test_proxy(host: str, port: int, username: str, password: str) -> bool:
    proxy_url = f"http://{username}:{password}@{host}:{port}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.ipify.org?format=json",
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                return resp.status == 200
    except Exception:
        return False


# ════════════════════════════════════════════════════════════════
#  دریافت یک پروکسی تصادفی برای Telethon
# ════════════════════════════════════════════════════════════════
async def get_random_proxy() -> dict | None:
    """
    هر بار مستقیم از Webshare یه پروکسی تازه می‌گیره.
    کش استفاده نمی‌کنه — همیشه fresh.
    """
    if not await is_proxy_enabled():
        return None

    cfg = await get_proxy_config()
    api_key = cfg.get("api_key")
    if not api_key:
        return None

    try:
        proxies = await fetch_proxies_from_webshare(api_key)
    except Exception as e:
        print(f"⚠️ Proxy fetch error: {e}")
        return None

    if not proxies:
        return None

    p = random.choice(proxies)
    return {
        "proxy_type": "socks5",
        "addr":       p["host"],
        "port":       int(p["port"]),
        "username":   p["username"],
        "password":   p["password"],
        "rdns":       True,
    }
