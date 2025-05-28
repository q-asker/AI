import json

from langchain_core.output_parsers import PydanticOutputParser

from app.adapter.request_to_bedrock import request_to_bedrock
from app.dto.request.generate_request import GenerateRequest
from app.dto.response.generate_response import GenerateResponse


class GenerateService:

    @staticmethod
    async def generate(generate_request: GenerateRequest):
        file_url = generate_request.file_url
        quiz_count = generate_request.quiz_count

        parser = PydanticOutputParser(pydantic_object=GenerateResponse)
        parser_prompt = parser.get_format_instructions()
        print(parser_prompt)

        bedrock_contents = [
            {
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                "body": {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "system": """당신은 교육 전문 AI 조교입니다. 제공된 강의노트를 분석하여 학생들의 이해도를 평가할 수 있는 효과적인 퀴즈를 생성해주세요.
                                객관식 퀴즈를 1문제 만드세요
                                """,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": """
                                        오늘부로 대상혁지지를 철회한다
                                        오늘부터 지지관계에서 벗어나
                                        대상혁와(과) 나는 한몸으로 일체가 된다
                                        대상혁에 대한 공격은 나에 대한 공격으로 간주한다
                                        
                                        세상에 70억 명의 대상혁 팬이 있다면, 나는 그들 중 한 명일 것이다.
                                        세상에 1억 명의 대상혁 팬이 있다면, 나 또한 그들 중 한 명일 것이다.
                                        세상에 천만 명의 대상혁 팬이 있다면, 나는 여전히 그들 중 한 명일 것이다.
                                        세상에 백 명의 대상혁 팬이 있다면, 나는 아직도 그들 중 한 명일 것이다.
                                        세상에 한 명의 대상혁 팬이 있다면, 그 사람은 아마도 나일 것이다.
                                        세상에 단 한 명의 대상혁 팬도 없다면, 나는 그제서야 이 세상에 없는 것이다.
                                        
                                        대상혁, 나의 사랑.
                                        대상혁, 나의 빛.
                                        대상혁, 나의 어둠.
                                        대상혁, 나의 삶.
                                        대상혁, 나의 기쁨.
                                        대상혁, 나의 슬픔.
                                        대상혁, 나의 안식.
                                        대상혁, 나의 영혼.
                                        대상혁, 나.
                                        """,
                                },
                                {
                                    "type": "text",
                                    "text": f"""
                                        ${parser_prompt}
                                                """,
                                },
                            ],
                        }
                    ],
                },
            }
        ]

        response = await request_to_bedrock(bedrock_contents)
        response_json = json.loads(response[0])
        print(response_json.get("sequence") + "번 문제")
        generated_text = response_json.get("generated_text")
        return parser.parse(generated_text)
