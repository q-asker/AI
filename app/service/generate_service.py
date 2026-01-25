import asyncio
import base64
import os
import random
from copy import deepcopy
from typing import List, Optional
from urllib.parse import urlparse

import fitz
import requests
from fastapi import HTTPException
from langchain_core.output_parsers import JsonOutputParser

from app.adapter.request_to_gpt import request_to_gpt_returning_text
from app.dto.model.problem_set import ProblemSet
from app.dto.request.generate_request import GenerateRequest
from app.dto.response.generate_response import (
    GenerateResponse,
    ProblemResponse,
)
from app.prompt import prompt_factory
from app.util.create_chunks import create_page_chunks
from app.util.gpt_utils import enforce_additional_properties_false
from app.util.logger import logger
from app.util.rate_limiter import rate_limiter
from app.util.timing import log_elapsed


class GenerateService:
    @staticmethod
    async def generate(generate_request: GenerateRequest):
        total_quiz_count = generate_request.quizCount
        page_numbers = generate_request.pageNumbers

        chunks = create_page_chunks(
            page_numbers, total_quiz_count, int(os.environ["MAX_CHUNK_COUNT"])
        )
        await rate_limiter.check_rate(len(chunks))

        problem_set_json_schema = enforce_additional_properties_false(
            deepcopy(ProblemSet.model_json_schema())
        )

        dok_level = generate_request.difficultyType
        quiz_type = generate_request.quizType
        uploaded_url = generate_request.uploadedUrl
        pdf_chunk_cache: dict[tuple[int, ...], str] = {}
        pdf_bytes = _load_pdf_content(uploaded_url)
        for i, chunk in enumerate(chunks):
            system_message = f"""
                당신은 대학 강의노트로부터 평가용 퀴즈를 생성하는 AI입니다.
                주어진 강의노트 내용을 분석하여 학생들의 이해도를 평가할 수 있는 효과적인 퀴즈를 정확히 {chunk.quiz_count}개 생성하세요.

                작성 규칙:
                - 한국어로 작성
                - 적극적으로 개행하여 가독성에 신경 쓸 것
                - 강의 노트를 참조하라는 문제 생성 금지 (예: "강의노트에 따르면", "본문을 참고하면" 등 금지)

                문제 생성 지침(품질/난이도):
                {prompt_factory.get_quiz_generation_guide(dok_level, quiz_type)}

                문항 형식(유형별 제약):
                {prompt_factory.get_quiz_format(quiz_type)}
                            """.strip()

            pages_key = tuple(chunk.referenced_pages)
            if pages_key not in pdf_chunk_cache:
                pdf_chunk_cache[pages_key] = _extract_pdf_pages_base64(
                    pdf_bytes, chunk.referenced_pages
                )
            pdf_chunk_base64 = pdf_chunk_cache[pages_key]
            if i < len(chunks) * 0.2:
                model = "gpt-4.1-mini"
            else:
                model = "gpt-5-mini"
            chunk.gpt_content = {
                "model": model,
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
                                "text": f"# 강의노트(PDF)",
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

        tasks = []
        for chunk in chunks:
            tasks.append(
                asyncio.create_task(
                    process_single_chunk(
                        chunk.gpt_content,
                        JsonOutputParser(pydantic_object=ProblemSet),
                        chunk.referenced_pages,
                        quiz_type,
                    )
                )
            )

        # 스트리밍 응답 처리
        number = 1
        try:
            for completed_task in asyncio.as_completed(tasks):
                try:
                    result: Optional[GenerateResponse] = await completed_task

                    if result:
                        for quiz in result.quiz:
                            quiz.number = number
                            number += 1
                        yield result.model_dump_json() + "\n"

                except Exception as e:
                    logger.error(f"Task processing failed: {e}")
                    # 하나가 실패해도 전체 스트림을 끊지 않고 다음 퀴즈 생성을 기다림
                    continue

        except Exception as e:
            logger.error(f"Critical streaming error: {e}")
            # 여기서 에러를 던지면 클라이언트(Spring)는 연결이 끊긴 것으로 인식
            raise HTTPException(status_code=500, detail="Streaming process failed")


async def process_single_chunk(
    gpt_request: dict,
    parser: JsonOutputParser,
    referenced_pages: List[int],
    quiz_type: str,
) -> Optional[GenerateResponse]:
    with log_elapsed(logger, "request_generate_quiz"):
        try:
            text_response = await request_to_gpt_returning_text(
                gpt_request, os.environ["GPT_REQUEST_TIMEOUT"]
            )

            if not text_response:
                return None

            # 파싱
            generated_data = parser.parse(text_response)

            # 구조 검증 및 변환
            quiz_list = generated_data.get("quiz", [])
            if not quiz_list:
                return None

            if not isinstance(quiz_list, list) or len(quiz_list) == 0:
                return None

            if len(quiz_list) > 0:
                first_selections = quiz_list[0].get("selections")
                if isinstance(first_selections, list) and len(first_selections) > 4:
                    return None

            # 문제 변환 (DTO 매핑)
            problem_responses = []
            for q in quiz_list:
                # 선택지 셔플 등 로직 수행
                selections = q.get("selections", [])
                if quiz_type in ["MULTIPLE", "BLANK"] and selections:
                    random.shuffle(selections)

                problem_responses.append(
                    ProblemResponse(
                        number=0,
                        title=q.get("title"),
                        selections=selections,
                        explanation=q.get("explanation"),
                        referencedPages=referenced_pages,
                    )
                )

            # 1~2개의 문제가 담긴 부분 응답 객체 반환
            return GenerateResponse(quiz=problem_responses)

        except Exception as e:
            logger.error(f"Chunk processing error: {e}")
            return None


def _extract_filename(uploaded_url: str) -> str:
    parsed = urlparse(uploaded_url)
    filename = os.path.basename(parsed.path)
    return filename or "document.pdf"


def _load_pdf_content(uploaded_url: str) -> bytes:
    response = requests.get(uploaded_url)
    response.raise_for_status()
    return response.content


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
