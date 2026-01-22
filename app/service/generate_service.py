import base64
import os
import random
from urllib.parse import urlparse
from copy import deepcopy
from typing import Any, List
from urllib.parse import urlparse

import fitz
import requests
from fastapi import HTTPException
from langchain_core.output_parsers import JsonOutputParser

from app.adapter.request_batch import request_responses_batch
from app.dto.model.generated_result import GeneratedResult
from app.dto.model.problem_set import ProblemSet
from app.dto.request.generate_request import GenerateRequest, QuizType
from app.dto.response.generate_response import (
    GenerateResponse,
    ProblemResponse,
)
from app.prompt import prompt_factory
from app.util.create_chunks import create_page_chunks
from app.util.logger import logger
from app.util.rate_limiter import rate_limiter
from app.util.timing import log_elapsed


def _enforce_additional_properties_false(schema: Any) -> Any:
    """
    OpenAI Structured Outputs(json_schema, strict=True) 제약:
    object 스키마는 additionalProperties=false 가 필요하다.
    Pydantic이 생성한 JSON Schema에 이를 재귀적으로 주입한다.
    """
    if isinstance(schema, list):
        return [_enforce_additional_properties_false(s) for s in schema]

    if not isinstance(schema, dict):
        return schema

    # object 타입이면 additionalProperties를 명시적으로 false로 고정
    if schema.get("type") == "object" and "additionalProperties" not in schema:
        schema["additionalProperties"] = False

    # 자주 등장하는 하위 스키마 컨테이너들 재귀 순회
    dict_children_keys = ("properties", "$defs", "definitions")
    for key in dict_children_keys:
        child = schema.get(key)
        if isinstance(child, dict):
            for k, v in child.items():
                child[k] = _enforce_additional_properties_false(v)

    list_children_keys = ("anyOf", "oneOf", "allOf", "prefixItems")
    for key in list_children_keys:
        child = schema.get(key)
        if isinstance(child, list):
            schema[key] = [_enforce_additional_properties_false(v) for v in child]

    # 단일 하위 스키마들
    for key in ("items", "not", "if", "then", "else"):
        child = schema.get(key)
        if isinstance(child, (dict, list)):
            schema[key] = _enforce_additional_properties_false(child)

    # additionalProperties가 dict로 오는 케이스도 대비(여기선 false로 고정하는 게 목적이지만, 안전하게 재귀 처리)
    ap = schema.get("additionalProperties")
    if isinstance(ap, dict):
        schema["additionalProperties"] = _enforce_additional_properties_false(ap)

    return schema


def _extract_filename(uploaded_url: str) -> str:
    parsed = urlparse(uploaded_url)
    filename = os.path.basename(parsed.path)
    return filename or "document.pdf"


def _load_pdf_content(uploaded_url: str) -> bytes:
    response = requests.get(uploaded_url)
    response.raise_for_status()
    return response.content


def _get_pdf_page_count(file_content: bytes) -> int:
    pdf_documents = fitz.open(stream=file_content, filetype="pdf")
    page_count = len(pdf_documents)
    pdf_documents.close()
    return page_count


def _extract_pdf_pages_base64(file_content: bytes, pages: List[int]) -> str:
    source = fitz.open(stream=file_content, filetype="pdf")
    target = fitz.open()
    for page_number in pages:
        page_index = page_number - 1
        if 0 <= page_index < len(source):
            target.insert_pdf(source, from_page=page_index, to_page=page_index)
    pdf_bytes = target.tobytes()
    target.close()
    source.close()
    return base64.b64encode(pdf_bytes).decode("ascii")


class GenerateService:
    @staticmethod
    async def generate(generate_request: GenerateRequest):
        quiz_count = generate_request.quizCount
        uploaded_url = generate_request.uploadedUrl
        total_quiz_count = generate_request.quizCount
        dok_level = generate_request.difficultyType
        quiz_type = generate_request.quizType
        page_numbers = generate_request.pageNumbers
        
        pdf_bytes = _load_pdf_content(uploaded_url)
        page_count = _get_pdf_page_count(pdf_bytes)
        if max_page_count < page_count:
            raise ValueError(f"페이지 수가 {max_page_count}페이지를 초과합니다.")

        pdf_bytes = _load_pdf_content(uploaded_url)
        page_count = _get_pdf_page_count(pdf_bytes)

        selected_pages = page_numbers
        if not selected_pages:
            selected_pages = list(range(1, page_count + 1))
        else:
            selected_pages = [p for p in selected_pages if 0 < p <= page_count]

        texts = [""] * (len(selected_pages) + 1)

        max_chunk_count = 15
        chunks = create_page_chunks(len(texts) - 1, total_quiz_count, max_chunk_count)
        await rate_limiter.check_rate(len(chunks))

        i = 0
        while i < len(chunks):
            chunk = chunks[i]

            while chunk.quiz_count > 2:
                # 기존 chunk 복제
                new_chunk = deepcopy(chunk)
                new_chunk.quiz_count = 2
                # 현재 인덱스 i 앞에 삽입
                chunks.insert(i, new_chunk)
                # 원본 chunk의 count 감소
                chunk.quiz_count -= 2
                # 삽입된 만큼 한 칸 이동
                i += 1

            i += 1

        page_index_source = selected_pages
        for chunk in chunks:
            chunk.referenced_pages = [
                page_index_source[i - 1]
                for i in chunk.referenced_pages
                if 1 <= i <= len(page_index_source)
            ]

        parser = JsonOutputParser(pydantic_object=ProblemSet)
        problem_set_json_schema = _enforce_additional_properties_false(
            deepcopy(ProblemSet.model_json_schema())
        )

        gpt_contents = []
        pdf_chunk_cache: dict[tuple[int, ...], str] = {}

        for chunk in chunks:
            system_message = f"""
                당신은 대학 강의노트로부터 평가용 퀴즈를 생성하는 AI입니다.
                주어진 강의노트 내용을 분석하여 학생들의 이해도를 평가할 수 있는 효과적인 퀴즈를 정확히 {chunk.quiz_count}개 생성하세요.

                작성 규칙:
                - 한국어로 작성
                - 마크다운을 활용해 가독성을 높힌다
                - 강의 노트를 참조하라는 문제 생성 금지 (예: "강의노트에 따르면", "본문을 참고하면" 등 금지)

                문제 생성 지침(품질/난이도):
                {prompt_factory.get_quiz_generation_guide(dok_level, quiz_type)}

                문항 형식(유형별 제약):
                {prompt_factory.get_quiz_format(quiz_type)}
                            """.strip()

            page_hint = (
                f"참조 페이지: {', '.join(map(str, chunk.referenced_pages))}"
                if chunk.referenced_pages
                else "참조 페이지: 없음"
            )
            pages_key = tuple(chunk.referenced_pages)
            if pages_key not in pdf_chunk_cache:
                pdf_chunk_cache[pages_key] = _extract_pdf_pages_base64(
                    pdf_bytes, chunk.referenced_pages
                )
            pdf_chunk_base64 = pdf_chunk_cache[pages_key]
            gpt_contents.append(
                {
                    "model": "gpt-4.1-mini",
                    "max_output_tokens": 10000,
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "problem_set",
                            "strict": True,
                            "schema": problem_set_json_schema,
                        }
                    },
                    "input": [
                        {"role": "system", "content": system_message},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": f"# 강의노트(PDF)\n\n{page_hint}",
                                },
                                {
                                    "type": "input_file",
                                    "filename": _extract_filename(uploaded_url),
                                    "file_data": f"data:application/pdf;base64,{pdf_chunk_base64}",
                                },
                            ],
                        },
                    ],
                }
            )

        with log_elapsed(logger, "request_generate_quiz"):
            timeout = int(os.environ["GPT_REQUEST_TIMEOUT"])
            texts = await request_responses_batch(gpt_contents, timeout=timeout)
            generated_results: List[GeneratedResult] = []
            for sequence, text in enumerate(texts, start=1):
                if not text:
                    continue
                generated_results.append(
                    GeneratedResult(sequence=sequence, generated_text=text)
                )

            if not generated_results:
                raise HTTPException(
                    status_code=429,
                    detail="모든 퀴즈 생성 요청이 실패하거나 시간 초과되었습니다.",
                )

        sorted_responses = []
        for i, generated_result in enumerate(generated_results):
            try:
                generated_text = parser.parse(generated_result.generated_text)

                # 방어: 첫 문제 선택지가 4개 초과면 폐기
                quiz = (
                    generated_text.get("quiz")
                    if isinstance(generated_text, dict)
                    else None
                )
                if isinstance(quiz, list) and len(quiz) > 0:
                    selections = (
                        quiz[0].get("selections") if isinstance(quiz[0], dict) else None
                    )
                    if isinstance(selections, list) and len(selections) > 4:
                        continue

                sorted_responses.append(
                    {
                        "sequence": generated_result.sequence,
                        "generated_text": generated_text,
                    }
                )
            except Exception as e:
                logger.error(f"Parsing error for response {i}: {e}")
                logger.error(f"Response content: {generated_result.generated_text}")
                continue

        sorted_responses.sort(key=lambda x: x["sequence"])

        seq_to_pages = {i + 1: chunk.referenced_pages for i, chunk in enumerate(chunks)}

        problem_responses: List[ProblemResponse] = []
        for generated_result in sorted_responses:
            quiz_data = generated_result.get("generated_text")
            quiz = quiz_data.get("quiz")
            for problem in quiz:
                if (
                    quiz_type == QuizType.MULTIPLE.value
                    or quiz_type == QuizType.BLANK.value
                ):
                    random.shuffle(problem.get("selections"))
                problem_responses.append(
                    ProblemResponse(
                        **problem,
                        referencedPages=seq_to_pages.get(
                            generated_result["sequence"], []
                        ),
                    )
                )

        real_sequence_number = 1
        for i, problem in enumerate(problem_responses):
            problem.number = real_sequence_number
            real_sequence_number += 1

        return GenerateResponse(quiz=problem_responses)
