import json
import os
from uuid import uuid4

import requests
from dotenv import load_dotenv

from app.dto.request.generate_request import GenerateRequest

load_dotenv()
aws_lambda_url = os.getenv("AWS_LAMBDA_URL")


class GenerateService:

    def generate(self, generate_request: GenerateRequest):

        file_url = generate_request.file_url
        quiz_count = generate_request.quiz_count

        # bedrock에 문제 생성 요청 그리고 결과
        quizzes = []
        batch_id = str(uuid4())
        for i in range(quiz_count):
            payload = {
                "batch_id": batch_id,
                "bedrock_content": {
                    "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                    "body": {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 1000,
                        "system": "당신은 교육 전문 AI 조교입니다. 제공된 강의노트를 분석하여 학생들의 이해도를 평가할 수 있는 효과적인 퀴즈를 생성해주세요.",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": """
                                또 모르지? 내 마음이 저 날씨처럼 바뀔지
                                날 나조차 다 알 수 없으니 (나나나나나나)
                                그게 뭐가 중요하니, 지금 네게 완전히
                                푹 빠졌단 게 중요한 거지 (나나나나나나)
                                아마 꿈만 같겠지만 분명 꿈이 아니야
                                달리 설명할 수 없는, 이건 사랑일 거야
                                방금 내가 말한 감정 감히 의심하지 마
                                그냥 좋다는 게 아냐 (what's after like?)
                                You-ooh and I-I, it's more than like
                                L 다음 또 O 다음 난, yeah, yeah, yeah
                                You-ooh and I-I, it's more than like (like)
                                What's after like?
                                What's after like?
                                조심해 두 심장에 핀 새파란 이 불꽃이
                                저 태양보다 뜨거울 테니 (나나나나나)
                                난 저 위로 또 아래로, 내 그래프는 폭이 커
                                Yeah, that's me (yeah, that's me)
                                두 번 세 번 피곤하게 자꾸 질문하지 마
                                내 장점이 뭔지 알아? 바로 솔직한 거야
                                방금 내가 말한 감정 감히 의심하지 마 (우우우우우)
                                그냥 좋다는 게 아냐 (what's after like?)
                                """,
                                    }
                                ],
                            }
                        ],
                    },
                },
            }

            response = requests.post(aws_lambda_url, json=payload).json()
            response_dict = json.loads(response)
            quizzes.append(response_dict["body"])

        return quizzes
