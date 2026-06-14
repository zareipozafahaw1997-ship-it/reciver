import asyncio, sys, os
sys.path.insert(0, "/home/ubuntu/bot")
from dotenv import load_dotenv
load_dotenv("/home/ubuntu/bot/.env")
from telethon import TelegramClient

API_ID    = int(os.getenv("API_ID"))
API_HASH  = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def main():
    client = TelegramClient("tmp_ids", API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)
    print("Channels the bot is in:")
    async for d in client.iter_dialogs():
        if d.is_channel or d.is_group:
            print(f"  {d.id} | {d.name}")
    await client.disconnect()

asyncio.run(main())
