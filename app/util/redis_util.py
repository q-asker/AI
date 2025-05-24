import json
import os

import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()
redis_host = os.getenv("REDIS_HOST")
redis_port = int(os.getenv("REDIS_PORT"))
redis_db = int(os.getenv("REDIS_DB"))
redis_password = os.getenv("REDIS_PASSWORD")

redis_client = redis.Redis(
    host=redis_host,
    port=redis_port,
    db=redis_db,
    password=redis_password,
    decode_responses=True,
)


class RedisUtil:
    @staticmethod
    async def save_bedrock_content(key, bedrock_content):
        await redis_client.set(key, json.dumps(bedrock_content, ensure_ascii=False))

    @staticmethod
    async def subscribe(key):
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"notify:{key}")
        return pubsub
