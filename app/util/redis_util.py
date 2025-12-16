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

    async def check_bedrock_rate(self, generate_count: int, key: str):
        WINDOW = 60
        LIMIT = 75

        now = int(time.time())
        window_start = now - WINDOW

        lock = self.redis_client.lock(f"lock:{key}", timeout=WINDOW)
        async with lock:
            pipe = await self.redis_client.pipeline()
            # 윈도우 밖의 오래된 항목 제거
            pipe.zremrangebyscore(key, 0, window_start)
            # 현재 윈도우 내 항목 수 조회
            pipe.zcard(key)
            removed, count = await pipe.execute()

            if count + generate_count > LIMIT:
                raise HTTPException(
                    status_code=429,
                    detail="요청이 많습니다. 잠시 후 다시 시도해주세요.",
                )

            now = time.time()
            mapping = {f"{now}-{uuid.uuid4()}": now for _ in range(generate_count)}

            pipe = await self.redis_client.pipeline()
            pipe.zadd(key, mapping)
            pipe.expire(key, WINDOW)
            await pipe.execute()
