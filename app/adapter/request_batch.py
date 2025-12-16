import asyncio
from typing import Callable, List, Optional, TypeVar, Union

from app.util.logger import logger

T = TypeVar("T")


async def request_batch(
    requests: List[dict],
    request_fn: Callable[[dict], T],
    *,
    concurrency: int = 10,
    return_exceptions: bool = False,
) -> List[Union[Optional[T], Exception]]:
    """여러 요청을 비동기로 한 번에 전송한다.

    - OpenAI SDK 호출은 동기 함수이므로 `asyncio.to_thread`로 감싼다.
    - 실패 시 기본은 `None`을 반환하고, `return_exceptions=True`면 예외 객체를 반환한다.
    """

    sem = asyncio.Semaphore(concurrency)

    async def _one(req: dict) -> Union[Optional[T], Exception]:
        async with sem:
            try:
                return await asyncio.to_thread(request_fn, req)
            except Exception as e:  # noqa: BLE001
                if return_exceptions:
                    return e
                logger.exception("Batch request 실패")
                return None

    tasks = [_one(r) for r in requests]
    return await asyncio.gather(*tasks)


async def request_text_batch(
    requests: List[dict],
    request_text_fn: Callable[[dict], str],
    *,
    concurrency: int = 10,
) -> List[Optional[str]]:
    """여러 요청을 비동기로 전송하고, 각 요청의 텍스트 결과를 반환한다."""
    results = await request_batch(
        requests,
        request_text_fn,
        concurrency=concurrency,
        return_exceptions=False,
    )
    # return_exceptions=False이므로 결과는 Optional[str]만 온다.
    return [r if isinstance(r, str) and r != "" else None for r in results]  # type: ignore[return-value]
