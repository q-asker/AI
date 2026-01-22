import asyncio
from typing import List, Optional

from openai import APITimeoutError  # AsyncOpenAI 타입 힌트용

from app.client.oepn_ai import get_gpt_client  # AsyncOpenAI를 반환한다고 가정
from app.util.logger import logger


async def request_responses_output_text(gpt_request: dict) -> str:
    """Responses API로 단건 요청을 비동기로 전송하고 텍스트만 추출한다."""
    resp = await get_gpt_client().responses.create(**gpt_request)

    text = getattr(resp, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text

    output = getattr(resp, "output", None)
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                for key in ("text", "output_text", "value"):
                    v = c.get(key)
                    if isinstance(v, str) and v.strip():
                        return v

    if not isinstance(text, str) or not text.strip():
        logger.warning("Responses API 응답에서 텍스트를 추출하지 못했습니다")
        return ""
    return text


async def request_responses_batch(
    requests: List[dict], timeout: float
) -> List[Optional[str]]:
    # 2. 개별 요청을 처리하는 내부 함수
    async def _one(req: dict) -> Optional[str]:
        try:
            text = await request_responses_output_text(req)
            return text if text else None
        except APITimeoutError:
            logger.error("OpenAI API Timeout")
            return None
        except Exception:
            logger.exception("Batch request 실패")
            return None

    # 3. 태스크 생성 (여기서는 쓰레드가 아닌 가벼운 Coroutine이 생성됨)
    tasks = [asyncio.create_task(_one(r)) for r in requests]
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
