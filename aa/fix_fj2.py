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
    
    # fix channel format
    await MongoDB.set_force_join("@Zloginbot", True)
    
    cfg = await MongoDB.get_force_join()
    print(f"Fixed: {cfg}")
    
    await RedisClient.disconnect()

asyncio.run(main())
