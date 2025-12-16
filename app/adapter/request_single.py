import os
from typing import Any, Optional

from dotenv import load_dotenv
from openai import OpenAI

from app.util.logger import logger

load_dotenv()

_gpt_client: Optional[OpenAI] = None


def get_gpt_client() -> OpenAI:
    """OpenAI 클라이언트를 싱글톤으로 제공한다."""
    global _gpt_client
    if _gpt_client is None:
        _gpt_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _gpt_client


def request_chat_completion(gpt_request: dict) -> Any:
    """Chat Completions API로 단건 요청을 전송하고 원본 응답을 반환한다."""
    return get_gpt_client().chat.completions.create(**gpt_request)


def request_chat_completion_text(gpt_request: dict) -> str:
    """Chat Completions API로 단건 요청을 전송하고 텍스트만 추출한다."""
    resp = request_chat_completion(gpt_request)
    return resp.choices[0].message.content


def request_responses(gpt_request: dict) -> Any:
    """Responses API로 단건 요청을 전송하고 원본 응답을 반환한다."""
    return get_gpt_client().responses.create(**gpt_request)


def extract_responses_output_text(resp: Any) -> str:
    """Responses API 응답에서 텍스트를 최대한 보수적으로 추출한다."""
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

    return ""


def request_responses_output_text(gpt_request: dict) -> str:
    """Responses API로 단건 요청을 전송하고 텍스트만 추출한다."""
    resp = request_responses(gpt_request)
    text = extract_responses_output_text(resp)
    if not isinstance(text, str) or not text.strip():
        logger.warning("Responses API 응답에서 텍스트를 추출하지 못했습니다")
    return text
