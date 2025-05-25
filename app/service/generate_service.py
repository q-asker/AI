from app.adapter.request_to_bedrock import request_to_bedrock
from app.dto.request.generate_request import GenerateRequest


class GenerateService:

    @staticmethod
    async def generate(generate_request: GenerateRequest):
        file_url = generate_request.file_url
        quiz_count = generate_request.quiz_count

        bedrock_contents = [
            {
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
                                                동해물과 백두산이 마르고 닳도록
                                                """,
                                }
                            ],
                        }
                    ],
                },
            },
            {
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
                                                하느님이 보우하사 우리나라 만세
                                                """,
                                }
                            ],
                        }
                    ],
                },
            },
            {
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
                                           무궁화 삼천리화려강산
                                                """,
                                }
                            ],
                        }
                    ],
                },
            },
            {
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
                                        대한 사람 대한으로 길이 보전하세
                                                        """,
                                }
                            ],
                        }
                    ],
                },
            },
        ]
        return await request_to_bedrock(bedrock_contents)
