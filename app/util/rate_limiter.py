import asyncio
import os
import time
from collections import deque

from fastapi import HTTPException


class LocalRateLimiter:
    def __init__(self, window_seconds: int = 60, limit: int = 75):
        self.window_seconds = window_seconds
        self.limit = limit
        # 요청 타임스탬프를 저장하는 큐
        self.requests = deque()
        # 동시성 제어를 위한 락
        self.lock = asyncio.Lock()

    async def check_rate(self, generate_count: int):
        now = time.time()
        window_start = now - self.window_seconds

        async with self.lock:
            # 1. 윈도우 밖의 오래된 타임스탬프 제거 (Clean up)
            while self.requests and self.requests[0] < window_start:
                self.requests.popleft()

            # 2. 현재 윈도우 내의 요청 수 확인
            if len(self.requests) + generate_count > self.limit:
                raise HTTPException(
                    status_code=429,
                    detail="요청이 많습니다. 잠시 후 다시 시도해주세요.",
                )

            # 3. 요청 허용: 새로운 청크 개수만큼 타임스탬프 추가
            for _ in range(generate_count):
                self.requests.append(now)


# 인스턴스 생성 (싱글톤으로 관리 권장)
rate_limiter = LocalRateLimiter(
    window_seconds=int(os.environ["RATE_LIMIT_WINDOW_SECONDS"]),
    limit=int(os.environ["RATE_LIMIT_MAX_REQUESTS"]),
)
