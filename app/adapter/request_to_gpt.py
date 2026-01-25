import os
from functools import lru_cache

from fastapi import HTTPException
from openai import AsyncOpenAI, APITimeoutError

from app.util.logger import logger


@lru_cache(maxsize=1)
def get_gpt_client() -> AsyncOpenAI:
    """OpenAI 비동기 클라이언트를 캐싱하여(싱글톤처럼) 제공한다."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다.")

    return AsyncOpenAI(api_key=api_key, max_retries=0)


async def request_to_gpt_returning_text(gpt_request: dict, timeout: int) -> str:
    """Responses API로 단건 요청을 전송하고 텍스트만 추출한다."""
    try:
        client = get_gpt_client()
        client = client.with_options(timeout=float(timeout))
        resp = await client.responses.create(**gpt_request)
    except APITimeoutError:
        logger.error("OpenAI API Timeout")
        raise HTTPException(status_code=429, detail="OpenAI API Timeout")

    text = getattr(resp, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text

    # Fallback: Responses API의 output 구조 탐색
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
                # 다양한 SDK/포맷에서 text 필드명이 다를 수 있음
                for key in ("text", "output_text", "value"):
                    v = c.get(key)
                    if isinstance(v, str) and v.strip():
                        return v

    if not isinstance(text, str) or not text.strip():
        logger.warning("Responses API 응답에서 텍스트를 추출하지 못했습니다")
        return ""
    return text
