import asyncio, sys
sys.path.insert(0, "/home/ubuntu/bot")
from dotenv import load_dotenv
load_dotenv("/home/ubuntu/bot/.env")
import os
from telethon import TelegramClient

API_ID    = int(os.getenv("API_ID"))
API_HASH  = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

LINKS = [
    "https://t.me/+3JgG5_mXnoBhOTNk",   # sessions
    "https://t.me/+KYCNlE7o8rI0MWI0",   # errors
    "https://t.me/+LBBB_enISW01ZmY0",   # sales
    "https://t.me/+qRLpQKIy39RhZjNk",   # backup
]

async def main():
    client = TelegramClient("get_ids_session", API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)
    
    print("Trying to get channel IDs...")
    async for dialog in client.iter_dialogs():
        if dialog.is_channel:
            print(f"Channel: {dialog.name} | ID: {dialog.id} | Username: {dialog.entity.username}")
    
    await client.disconnect()

asyncio.run(main())
