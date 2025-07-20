import json
import time
from typing import List

from langchain_core.output_parsers import JsonOutputParser

from app.adapter.request_to_bedrock import request_to_bedrock
from app.dto.model.problem_set import ProblemSet
from app.dto.request.generate_request import GenerateRequest
from app.dto.request.search_request import SearchRequest
from app.dto.response.generate_response import (
    GenerateResponse,
    ProblemResponse,
)
from app.prompt.quiz_dok_guideline import get_quiz_generation_guide
from app.prompt.quiz_format import get_quiz_format
from app.util.create_chunks import create_chunks
from app.util.logger import logger
from app.util.parsing import process_file
from app.util.redis_util import RedisUtil

redis_util = RedisUtil()


class GenerateService:

    @staticmethod
    async def search_and_generate(search_request: SearchRequest):
        query = search_request.query
        bedrock_contents = [
            {
                "modelId": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                "body": {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 5000,
                    "system": f"""
                            주어지는 내용을 바탕으로 적절한 참고 사이트를 찾아주세요""",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"""
                                        ${query}
                                        """,
                                }
                            ],
                        }
                    ],
                },
            }
        ]

        await redis_util.check_bedrock_rate(len(bedrock_contents), "rl:bedrock:global")

        start = time.time()
        generated_result = await request_to_bedrock(bedrock_contents, mcp_mode=True)
        end = time.time()
        elapsed = end - start
        logger.info(f"소요 시간: {elapsed:.4f}초")
        return json.loads(generated_result[0])

    @staticmethod
    async def generate(generate_request: GenerateRequest):
        uploaded_url = generate_request.uploadedUrl
        total_quiz_count = generate_request.quizCount
        dok_level = generate_request.difficultyType
        quiz_type = generate_request.quizType
        page_numbers = generate_request.pageNumbers

        texts = process_file(uploaded_url, page_numbers)

        minimum_page_text_length_per_chunk = 500
        max_chunk_count = 25
        chunks = create_chunks(
            texts, total_quiz_count, minimum_page_text_length_per_chunk, max_chunk_count
        )

        await redis_util.check_bedrock_rate(len(chunks), "rl:bedrock:global")

        for chunk in chunks:
            chunk.referenced_pages = [
                page_numbers[i - 1]
                for i in chunk.referenced_pages
                if 1 <= i <= len(page_numbers)
            ]

        parser = JsonOutputParser(pydantic_object=ProblemSet)
        format_instructions = parser.get_format_instructions()

        bedrock_contents = []
        for chunk in chunks:
            bedrock_contents.append(
                {
                    "modelId": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                    "body": {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 5000,
                        "system": f"""
                        주어진 강의노트 내용을 분석하여 학생들의 이해도를 평가할 수 있는 효과적인 퀴즈 {chunk.quiz_count}개를 생성해주세요.
                        문제 생성 지침:
                        {get_quiz_generation_guide(dok_level, quiz_type)}

                        응답 요구사항:
                        - 한국어로 작성
                        - JSON 형식으로만 출력 (다른 텍스트 포함 금지)
                        - 강의노트의 핵심 개념을 다루는 문제
                        - 학습 목표와 연결된 평가 문항
                        {get_quiz_format(quiz_type)}
                        JSON 구조:
                        {format_instructions}""",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"""
                                                    # 강의노트
                                                    {chunk.text}
                                                """,
                                    }
                                ],
                            }
                        ],
                    },
                }
            )

        start = time.time()
        generated_results = await request_to_bedrock(bedrock_contents)
        end = time.time()
        elapsed = end - start
        logger.info(f"소요 시간: {elapsed:.4f}초")

        sorted_responses = []
        for i, generated_result in enumerate(generated_results):
            try:
                generated_text = parser.parse(generated_result.generated_text)
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

        problem_responses: List[ProblemResponse] = []
        for i, generated_result in enumerate(sorted_responses):
            quiz_data = generated_result.get("generated_text")
            quiz = quiz_data.get("quiz")
            for problem in quiz:
                problem_responses.append(
                    ProblemResponse(
                        **problem, referencedPages=chunks[i].referenced_pages
                    )
                )

        for i, problem in enumerate(problem_responses):
            problem.number = i + 1

        return GenerateResponse(quiz=problem_responses)
