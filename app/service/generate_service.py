import json
import time

from langchain_core.output_parsers import JsonOutputParser

from app.adapter.request_to_bedrock import request_to_bedrock
from app.dto.request.generate_request import GenerateRequest
from app.dto.response.generate_response import GenerateResponse
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

        parser = JsonOutputParser(pydantic_object=GenerateResponse)
        format_instructions = parser.get_format_instructions()

        bedrock_contents = []
        for chunk in chunks:
            bedrock_contents.append(
                {
                    "modelId": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                    "body": {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 20000,
                        "system": f"당신은 교육 전문 AI 조교입니다. 제공된 강의노트를 분석하여 학생들의 이해도를 평가할 수 있는 효과적인 퀴즈를 {chunk.quiz_count}개 생성해주세요. JSON 이외의 텍스트는 절대 출력하지 마세요.",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"""
                                            # FORMAT
                                            {format_instructions}

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
