import json
import time

from langchain_core.output_parsers import JsonOutputParser

from app.adapter.request_to_bedrock import request_to_bedrock
from app.adapter.summary_bedrock import create_summary
from app.dto.request.generate_request import GenerateRequest
from app.dto.response.generate_response import GenerateResponse
from app.util.create_chunks import create_chunks
from app.util.logger import logger
from app.util.parsing import process_file


class GenerateService:

    @staticmethod
    async def generate(generate_request: GenerateRequest):
        uploaded_url = generate_request.uploadedUrl
        quiz_count = generate_request.quizCount

        # pydantic output parser 구현
        parser = JsonOutputParser(pydantic_object=GenerateResponse)
        format_instructions = parser.get_format_instructions()

        bedrock_contents = []
        full_text = process_file(uploaded_url)
        summary = await create_summary(full_text)

        quiz_count_per_chunk = 5
        if quiz_count % quiz_count_per_chunk == 0:
            quiz_count_last_chunk = quiz_count_per_chunk
        else:
            quiz_count_last_chunk = quiz_count % quiz_count_per_chunk

        chunks = await create_chunks(full_text, quiz_count, quiz_count_per_chunk)

        for i, chunk in enumerate(chunks, start=1):
            if len(chunks) != i:
                cur_quiz_count_per_chunk = quiz_count_per_chunk
            else:
                cur_quiz_count_per_chunk = quiz_count_last_chunk
            bedrock_contents.append(
                {
                    "modelId": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                    "body": {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 20000,
                        "system": f"당신은 교육 전문 AI 조교입니다. 요약과 함께 제공된 강의노트를 분석하여 학생들의 이해도를 평가할 수 있는 효과적인 퀴즈를 {cur_quiz_count_per_chunk}개 생성해주세요. JSON 이외의 텍스트는 절대 출력하지 마세요.",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"""
                                            # FORMAT
                                            {format_instructions}

                                            # 요약
                                            {summary}

                                            # 강의노트
                                            {chunk}
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
        logger.info(
            f"청크 당 퀴즈 카운트 {quiz_count_per_chunk}개 일 때 소요 시간: {elapsed:.4f}초"
        )

        all_quizzes = []
        for response in responses:
            quiz_data = json.loads(response).get("generated_text")
            parsed_quiz = json.loads(quiz_data)
            all_quizzes.extend(parsed_quiz.get("quiz", []))

        for i, quiz in enumerate(all_quizzes):
            quiz["number"] = i + 1

        for quiz in all_quizzes:
            logger.info(quiz)

        return GenerateResponse(quiz=all_quizzes)
