import json
import os
import time
import uuid

import redis.asyncio as redis
from dotenv import load_dotenv
from fastapi import HTTPException

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

    async def check_bedrock_rate(self, generate_count: int, key: str):
        WINDOW = 60
        LIMIT = 75

        now = int(time.time())
        window_start = now - WINDOW

        lock = self.redis_client.lock(f"lock:{key}", timeout=WINDOW)
        async with lock:
            pipe = await self.redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            removed, count = await pipe.execute()

            if count + generate_count > LIMIT:
                raise HTTPException(
                    status_code=429,
                    detail="요청이 많습니다. 잠시 후 다시 시도해주세요.",
                )

            pipe = await self.redis_client.pipeline()
            for _ in range(generate_count):
                member = f"{now}-{uuid.uuid4()}"
                pipe.zadd(key, {member: now})
            # 윈도우 TTL 갱신
            pipe.expire(key, WINDOW)
            await pipe.execute()
