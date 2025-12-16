import json
import os
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI

from app.util.logger import logger

load_dotenv()

gpt_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def request_search_references(gpt_request: dict) -> Dict[str, Any]:
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
        text = resp.choices[0].message.content
        return json.loads(text)
    except Exception:
        logger.exception("Search references GPT 호출 실패")
        raise

