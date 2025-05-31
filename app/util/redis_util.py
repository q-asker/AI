import json
import os

import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()
redis_host = os.getenv("REDIS_HOST")
redis_port = int(os.getenv("REDIS_PORT"))
redis_db = int(os.getenv("REDIS_DB"))
redis_password = os.getenv("REDIS_PASSWORD")


class RedisUtil:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True,
        )

    async def save_bedrock_content(self, key, bedrock_content):
        await self.redis_client.set(
            key, json.dumps(bedrock_content, ensure_ascii=False), ex=600
        )

    async def subscribe(self, key):
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(key)
        return pubsub
