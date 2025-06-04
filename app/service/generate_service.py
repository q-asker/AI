import json
import time
from typing import List

from langchain_core.output_parsers import JsonOutputParser

from app.adapter.request_to_bedrock import request_to_bedrock
from app.dto.model.problem_set import ProblemSet
from app.dto.request.generate_request import GenerateRequest
from app.dto.response.generate_response import (
    GenerateResponse,
    ProblemResponse,
)
from app.util.create_chunks import create_chunks
from app.util.logger import logger
from app.util.parsing import process_file


class GenerateService:

    @staticmethod
    async def generate(generate_request: GenerateRequest):
        uploaded_url = generate_request.uploadedUrl
        total_quiz_count = generate_request.quizCount

        texts = process_file(uploaded_url)

        minimum_page_text_length_per_chunk = 500
        max_chunk_count = 10
        chunks = create_chunks(
            texts, total_quiz_count, minimum_page_text_length_per_chunk, max_chunk_count
        )

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
                        응답 요구사항:
                        - 한국어로 작성
                        - JSON 형식으로만 출력 (다른 텍스트 포함 금지)
                        - 강의노트의 핵심 개념을 다루는 문제
                        - 학습 목표와 연결된 평가 문항
                        - 객관식 문제로, 4개의 선택지 제공
                        - 정답은 하나로 설정
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
        responses = await request_to_bedrock(bedrock_contents)
        end = time.time()
        elapsed = end - start
        logger.info(f"소요 시간: {elapsed:.4f}초")

        sorted_responses = []
        for i, response in enumerate(responses):
            quiz_data = json.loads(response)
            generated_text = parser.parse(quiz_data.get("generated_text"))
            sorted_responses.append(
                {
                    "sequence": quiz_data.get("sequence"),
                    "generated_text": generated_text,
                }
            )

        sorted_responses.sort(key=lambda x: x["sequence"])

        problem_responses: List[ProblemResponse] = []
        for i, response in enumerate(sorted_responses):
            quiz_data = response.get("generated_text")
            quiz = quiz_data.get("quiz")
            for problem in quiz:
                problem_responses.append(
                    ProblemResponse(
                        **problem, referencedPages=chunks[i].referenced_pages
                    )
                )

        for i, problem in enumerate(problem_responses):
            problem.number = i + 1

        for problem in problem_responses:
            logger.info(problem)

        generation_response = GenerateResponse(quiz=problem_responses)
        return generation_response
