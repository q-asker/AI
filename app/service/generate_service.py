import json
import random
import time
from copy import deepcopy
from typing import List

from langchain_core.output_parsers import JsonOutputParser

from app.adapter.request_generate_quiz_to_bedrock import (
    request_generate_quiz,
)
from app.adapter.request_generate_specific_explanation_to_bedrock import (
    request_specific_explanation_to_bedrock,
)
from app.dto.model.problem_set import ProblemSet
from app.dto.request.generate_request import GenerateRequest
from app.dto.request.search_request import SearchRequest
from app.dto.request.specific_explanation_request import SpecificExplanationRequest
from app.dto.response.generate_response import (
    GenerateResponse,
    ProblemResponse,
)
from app.dto.response.specific_explanation_response import SpecificExplanationResponse
from app.prompt import prompt_factory
from app.util.create_chunks import create_chunks
from app.util.logger import logger
from app.util.parsing import process_file
from app.util.redis_util import RedisUtil

redis_util = RedisUtil()


class GenerateService:
    @staticmethod
    async def generate_specific_explanation(
            specific_explanation_request: SpecificExplanationRequest,
    ):
        title = specific_explanation_request.title
        selections = specific_explanation_request.selections
        print(f"title: {title}")
        selection_text = ""
        for idx, s in enumerate(selections, start=1):
            answer_tag = "(정답)" if s.correct else ""
            selection_text += f"{idx}. {s.content} {answer_tag}\n"
        print(f"selection_text: {selection_text}")
        bedrock_contents = [
            {
                "modelId": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                "body": {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 50000,
                    "system": f"""
                                아래는 하나의 객관식 문제와 4개의 선택지입니다. 각 선택지는 정답 여부도 함께 제공됩니다.
                                문제를 바탕으로, 왜 해당 정답이 맞는지, 다른 선택지들은 왜 틀렸는지를 논리적으로 설명해주세요.
                                - 왜 해당 선택지가 정답인지 설명하세요.
                                - 나머지 선택지들은 왜 틀렸는지 설명하세요.
                                - 형식은 단순한 서술문으로, JSON 형태로 응답하지 마세요.
                                - 하나의 글로 말하세요.
                                - 검색한 경우, 그 출처를 url 형식으로 밝히세요.
                    """,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"""
                                            문제: {title}
                                            선택지:
                                            {selection_text}
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
        generated_result = await request_specific_explanation_to_bedrock(
            bedrock_contents
        )
        end = time.time()
        elapsed = end - start
        logger.info(f"소요 시간: {elapsed:.4f}초")
        raw_text = (
            generated_result[0].generated_text
            if hasattr(generated_result[0], "generated_text")
            else str(generated_result[0])
        )
        try:
            parsed_json = json.loads(raw_text)
            explanation_text = parsed_json.get("specific_explanation", raw_text)
        except json.JSONDecodeError:
            explanation_text = raw_text
        print(f"generated_result: {generated_result}")
        return SpecificExplanationResponse(specific_explanation=explanation_text)

    @staticmethod
    async def search_and_generate(search_request: SearchRequest):
        query = search_request.query
        bedrock_contents = [
            {
                "modelId": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                "body": {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 10000,
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
        generated_result = await request_generate_quiz(bedrock_contents)
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
        max_chunk_count = 15
        # TODO min_quiz_size = 3
        chunks = create_chunks(
            texts, total_quiz_count, minimum_page_text_length_per_chunk, max_chunk_count
        )

        await redis_util.check_bedrock_rate(len(chunks), "rl:bedrock:global")

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

                i += 1  # 삽입된 만큼 한 칸 이동

            i += 1

        for chunk in chunks:
            chunk.referenced_pages = [
                page_numbers[i - 1]
                for i in chunk.referenced_pages
                if 1 <= i <= len(page_numbers)
            ]

        parser = JsonOutputParser(pydantic_object=ProblemSet)
        format_instructions = parser.get_format_instructions()

        gpt_contents = []

        for chunk in chunks:
            gpt_contents.append(
                {
                    "model": "gpt-4.1-mini",
                    "temperature": 0.3,
                    "max_completion_tokens": 10000,
                    "messages": [
                        {
                            "role": "system",
                            "content": f"""
        당신은 대학 강의노트로부터 평가용 퀴즈를 생성하는 AI입니다.
        주어진 강의노트 내용을 분석하여 학생들의 이해도를 평가할 수 있는 효과적인 퀴즈를 {chunk.quiz_count}개 생성하세요.

        문제 생성 지침:
        {prompt_factory.get_quiz_generation_guide(dok_level, quiz_type)}

        ### 출력 요구 사항
        - 한국어로 작성
        - 강의 노트를 참조하라는 문제 생성 금지
        - 출력은 JSON 형식으로만 출력 (다른 텍스트 
    포함 금지)
         {prompt_factory.get_quiz_format(quiz_type)}

        아래 JSON 형식에 정확히 맞춰서 출력하세요:
        JSON 구조(스키마 설명):
        {format_instructions}
                            """.strip(),
                        },
                        {
                            "role": "user",
                            "content": f"""# 강의노트

                             {chunk.text}
                            """.strip(),
                        },
                    ],
                }
            )

        start = time.time()
        generated_results = await request_generate_quiz(gpt_contents)
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
                random.shuffle(problem.get("selections"))
                problem_responses.append(
                    ProblemResponse(
                        **problem, referencedPages=chunks[i].referenced_pages
                    )
                )

        real_sequence_number = 1
        for i, problem in enumerate(problem_responses):
            problem.number = real_sequence_number
            real_sequence_number += 1

        return GenerateResponse(quiz=problem_responses)
