from dotenv import load_dotenv
from fastapi import HTTPException
from openai import APITimeoutError
import os

from app.client.oepn_ai import get_gpt_client
from app.util.logger import logger

load_dotenv()


def request_responses_output_text(gpt_request: dict) -> str:
    """Responses API로 단건 요청을 전송하고 텍스트만 추출한다."""
    timeout = float(os.getenv("TIME_OUT", 40))
    try:
        resp = get_gpt_client().responses.create(timeout=timeout, **gpt_request)
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
