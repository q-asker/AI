import asyncio
from typing import List, Optional

from app.client.oepn_ai import get_gpt_client
from app.util.logger import logger


def request_chat_completion_text(gpt_request: dict) -> str:
    """Chat Completions API로 단건 요청을 전송하고 텍스트만 추출한다."""
    logger.info("GPT 요청: %s", gpt_request)
    resp = get_gpt_client().chat.completions.create(**gpt_request)
    return resp.choices[0].message.content


async def request_text_batch(
    requests: List[dict],
) -> List[Optional[str]]:
    async def _one(req: dict) -> Optional[str]:
        try:
            text = await asyncio.to_thread(request_chat_completion_text, req)
            return text if isinstance(text, str) and text != "" else None
        except Exception:
            logger.exception("Batch request 실패")
            return None

    tasks = [_one(r) for r in requests]
    return await asyncio.gather(*tasks)
