import asyncio, sys
sys.path.insert(0, "/home/ubuntu/bot")
from dotenv import load_dotenv
load_dotenv("/home/ubuntu/bot/.env")
from database.mongo import MongoDB
from database.redis_client import RedisClient

async def main():
    await MongoDB.connect()
    await RedisClient.connect()
    cfg = await MongoDB.get_channels()
    for k,v in cfg.items():
        print(f"  {k}: {v}")
    await RedisClient.disconnect()

asyncio.run(main())
