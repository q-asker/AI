import asyncio
import os
from typing import List, Optional

from openai import APITimeoutError

from app.client.oepn_ai import get_gpt_client
from app.util.logger import logger


def request_chat_completion_text(gpt_request: dict) -> str:
    """Chat Completions API로 단건 요청을 전송하고 텍스트만 추출한다."""
    logger.info("GPT 요청: %s", gpt_request)
    resp = get_gpt_client().chat.completions.create(**gpt_request)
    return resp.choices[0].message.content


async def request_text_batch(
    requests: List[dict],
    timeout: float
) -> List[Optional[str]]:
    async def _one(req: dict) -> Optional[str]:
        try:
            text = await asyncio.to_thread(request_chat_completion_text, req)
            return text if isinstance(text, str) and text != "" else None
        except APITimeoutError:
            logger.error("OpenAI API Timeout")
            return None
        except Exception:
            logger.exception("Batch request 실패")
            return None

    tasks = [asyncio.create_task(_one(r)) for r in requests]

    done, pending = await asyncio.wait(tasks, timeout=timeout)

    if pending:
        logger.error(f"Batch processing timed out after {timeout} seconds. {len(pending)} tasks incomplete.")
        for task in pending:
            task.cancel()

    results = []
    for task in tasks:
        if task in done:
            try:
                results.append(task.result())
            except Exception:
                logger.exception("Task completed with exception")
                results.append(None)
        else:
            results.append(None)

    return results
