import asyncio
import sys
sys.path.insert(0, "/home/ubuntu/bot")
from dotenv import load_dotenv
load_dotenv("/home/ubuntu/bot/.env")
import os
from telethon import TelegramClient

API_ID    = int(os.getenv("API_ID"))
API_HASH  = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
TEST_USER = int(os.getenv("ADMIN_IDS", "0").split(",")[0])

async def main():
    client = TelegramClient("test_session", API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)
    
    channel = "@Zloginbot"
    print(f"Testing get_permissions for user {TEST_USER} in {channel}")
    try:
        perms = await client.get_permissions(channel, TEST_USER)
        print(f"Result: {perms}")
        print("User IS member")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
    
    await client.disconnect()

asyncio.run(main())
