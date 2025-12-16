import asyncio
import os
from typing import List

from dotenv import load_dotenv
from openai import OpenAI

from app.dto.model.generated_result import GeneratedResult
from app.util.logger import logger

load_dotenv()

# GPT 클라이언트 (환경변수 OPENAI_API_KEY 사용)
gpt_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_gpt(gpt_request: dict) -> str:
    model = gpt_request.get("model") or "gpt-5-mini"
    messages = gpt_request.get("messages")
    if not messages:
        raise ValueError("gpt_request.messages is required")

    kwargs = {"model": model, "messages": messages}

    response_format = gpt_request.get("response_format")
    if response_format is not None:
        kwargs["response_format"] = response_format

    temperature = gpt_request.get("temperature")
    if temperature is not None:
        kwargs["temperature"] = temperature

    max_completion_tokens = gpt_request.get("max_completion_tokens")
    if max_completion_tokens is not None:
        kwargs["max_completion_tokens"] = max_completion_tokens

    try:
        resp = gpt_client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content
    except Exception:
        logger.exception("Specific explanation GPT 호출 실패")
        return "fail"


async def request_specific_explanation(gpt_requests: List[dict]) -> List[GeneratedResult]:
    tasks = [asyncio.to_thread(call_gpt, req) for req in gpt_requests]
    texts = await asyncio.gather(*tasks)

    results: List[GeneratedResult] = []
    for i, text in enumerate(texts, start=1):
        if text and text != "fail":
            results.append(GeneratedResult(sequence=i, generated_text=text))
    return results
