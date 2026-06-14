import asyncio
import sys
sys.path.insert(0, "/home/ubuntu/bot")

from dotenv import load_dotenv
load_dotenv("/home/ubuntu/bot/.env")

from database.mongo import MongoDB
from database.redis_client import RedisClient

async def main():
    await MongoDB.connect()
    await RedisClient.connect()
    
    cfg = await MongoDB.get_force_join()
    print(f"force_join config: {cfg}")
    
    channels = await MongoDB.get_channels()
    print(f"fj_enabled: {channels.get('fj_enabled')}")
    print(f"fj_channel: {channels.get('fj_channel')}")
    
    await RedisClient.disconnect()

asyncio.run(main())
