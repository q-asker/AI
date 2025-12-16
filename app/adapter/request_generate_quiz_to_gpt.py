import asyncio
import json
import os
from typing import List, Optional

from dotenv import load_dotenv
from langchain_core.output_parsers import JsonOutputParser
from openai import OpenAI

from app.dto.model.generated_result import GeneratedResult
from app.dto.model.problem_set import ProblemSet
from app.util.logger import logger

load_dotenv()

# GPT 클라이언트 (환경변수 OPENAI_API_KEY 사용)
gpt_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_json(raw: str) -> str:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return raw[start : end + 1]


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
        logger.exception("GPT 호출 실패")
        return "fail"


def validate_and_parse_quiz_json(generated_text: str, sequence: int) -> Optional[GeneratedResult]:
    try:
        extracted = extract_json(generated_text)
        if not extracted:
            return None

        parser = JsonOutputParser(pydantic_object=ProblemSet)
        parsed = parser.parse(extracted)

        # 방어: 첫 문제 선택지가 4개 초과면 폐기
        if parsed.get("quiz") and len(parsed.get("quiz")) > 0:
            selections = parsed.get("quiz")[0].get("selections")
            if selections and len(selections) > 4:
                return None

        return GeneratedResult(sequence=sequence, generated_text=extracted)
    except Exception as e:
        logger.error(f"Error parsing result: {e}")
        return None


async def _process_single(gpt_request: dict, sequence: int) -> Optional[GeneratedResult]:
    generated_text = await asyncio.to_thread(call_gpt, gpt_request)
    if generated_text == "fail":
        return None
    return validate_and_parse_quiz_json(generated_text, sequence)


async def request_generate_quiz(gpt_requests: List[dict]) -> List[GeneratedResult]:
    tasks = [_process_single(req, i + 1) for i, req in enumerate(gpt_requests)]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]
