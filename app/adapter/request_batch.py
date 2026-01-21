import asyncio
from typing import List, Optional

from openai import APITimeoutError  # AsyncOpenAI 타입 힌트용

from app.client.oepn_ai import get_gpt_client  # AsyncOpenAI를 반환한다고 가정
from app.util.logger import logger


# 1. 동기 함수 제거 -> 비동기 함수로 변경
async def request_chat_completion_text(gpt_request: dict) -> str:
    """AsyncOpenAI를 사용하여 비동기로 요청을 전송한다."""
    logger.info("GPT 요청: %s", gpt_request)  # 로그가 너무 많으면 성능 저하 원인이 됨

    # await 키워드 사용 (Non-blocking)
    resp = await get_gpt_client().chat.completions.create(**gpt_request)
    return resp.choices[0].message.content


async def request_text_batch(
    requests: List[dict], timeout: float
) -> List[Optional[str]]:
    # 2. 개별 요청을 처리하는 내부 함수
    async def _one(req: dict) -> Optional[str]:
        try:
            text = await request_chat_completion_text(req)
            return text if text else None
        except APITimeoutError:
            logger.error("OpenAI API Timeout")
            return None
        except Exception:
            logger.exception("Batch request 실패")
            return None

    # 3. 태스크 생성 (여기서는 쓰레드가 아닌 가벼운 Coroutine이 생성됨)
    tasks = [asyncio.create_task(_one(r)) for r in requests]

    # 4. asyncio.wait로 타임아웃 관리 (기존 로직 유지)
    done, pending = await asyncio.wait(tasks, timeout=timeout)

    if pending:
        logger.error(
            f"Batch processing timed out after {timeout} seconds. {len(pending)} tasks incomplete."
        )
        for task in pending:
            task.cancel()  # 대기 중인 코루틴 취소

    # 5. 결과 수집
    results = []
    for task in tasks:
        if task in done:
            try:
                # task.result()는 즉시 값을 반환함 (이미 완료되었으므로)
                results.append(task.result())
            except asyncio.CancelledError:
                results.append(None)
            except Exception:
                logger.exception("Task completed with exception")
                results.append(None)
        else:
            results.append(None)

    return results
