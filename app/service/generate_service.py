import random
from copy import deepcopy
from typing import List

from langchain_core.output_parsers import JsonOutputParser

from app.adapter.request_batch import request_text_batch
from app.adapter.request_single import request_chat_completion_text
from app.dto.model.generated_result import GeneratedResult
from app.dto.model.problem_set import ProblemSet
from app.dto.request.generate_request import GenerateRequest, QuizType
from app.dto.response.generate_response import (
    GenerateResponse,
    ProblemResponse,
)
from app.prompt import prompt_factory
from app.util.create_chunks import create_chunks
from app.util.logger import logger
from app.util.parsing import process_file
from app.util.redis_util import RedisUtil
from app.util.timing import log_elapsed

redis_util = RedisUtil()


class GenerateService:
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
        problem_set_json_schema = ProblemSet.model_json_schema()

        gpt_contents = []

        for chunk in chunks:
            gpt_contents.append(
                {
                    "model": "gpt-5-mini",
                    "temperature": 0.3,
                    "max_completion_tokens": 10000,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "problem_set",
                            "strict": True,
                            "schema": problem_set_json_schema,
                        },
                    },
                    "messages": [
                        {
                            "role": "system",
                            "content": f"""
                                당신은 대학 강의노트로부터 평가용 퀴즈를 생성하는 AI입니다.
                                주어진 강의노트 내용을 분석하여 학생들의 이해도를 평가할 수 있는 효과적인 퀴즈를 정확히 {chunk.quiz_count}개 생성하세요.

                                작성 규칙:
                                - 한국어로 작성
                                - 강의 노트를 참조하라는 문제 생성 금지 (예: "강의노트에 따르면", "본문을 참고하면" 등 금지)

                                문제 생성 지침(품질/난이도):
                                {prompt_factory.get_quiz_generation_guide(dok_level, quiz_type)}

                                문항 형식(유형별 제약):
                                {prompt_factory.get_quiz_format(quiz_type)}
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

        with log_elapsed(logger, "request_generate_quiz"):
            texts = await request_text_batch(gpt_contents, request_chat_completion_text)
            generated_results: List[GeneratedResult] = []
            for sequence, text in enumerate(texts, start=1):
                if not text:
                    continue
                generated_results.append(
                    GeneratedResult(sequence=sequence, generated_text=text)
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

        # sequence(1-based) -> referenced pages 매핑 (응답 누락 시에도 안전)
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
