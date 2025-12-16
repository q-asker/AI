import logging
import time
from contextlib import contextmanager
from typing import Iterator, Optional


@contextmanager
def log_elapsed(
    logger: logging.Logger,
    name: Optional[str] = None,
    *,
    level: str = "info",
    prefix: str = "소요 시간",
) -> Iterator[None]:
    """
    코드 블록 실행 시간을 측정해 로그로 남깁니다.

    사용 예)
        with log_elapsed(logger, "request_generate_quiz"):
            result = await request_generate_quiz(...)
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        msg = (
            f"{prefix}: {elapsed:.4f}초"
            if not name
            else f"{name} {prefix}: {elapsed:.4f}초"
        )
        log_fn = getattr(logger, level, None)
        if callable(log_fn):
            log_fn(msg)
        else:
            logger.info(msg)
