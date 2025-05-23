from app.dto.model.problem import Problem
from app.dto.model.selection import Selection
from app.dto.request.generate_request import GenerateRequest
from app.dto.response.generate_response import GenerateResponse


class GenerateService:

    def generate(self, generate_request: GenerateRequest):

        file_url = generate_request.file_url
        quiz_count = generate_request.quiz_count

        # bedrock에 문제 생성 요청 그리고 결과

        return GenerateResponse(
            title="인해대학교 문제집",
            problems=[
                Problem(
                    title="인하대학교 창립 연도는?",
                    explanation="인하대학교는 1954년에 설립되었습니다.",
                    selections=[
                        Selection(
                            content="1954년",
                            correct=True,
                        ),
                        Selection(
                            content="1955년",
                            correct=False,
                        ),
                        Selection(
                            content="1956년",
                            correct=False,
                        ),
                        Selection(
                            content="1957년",
                            correct=False,
                        ),
                    ],
                ),
                Problem(
                    title="인하대학교 마스코트는?",
                    explanation="안뇽이라는 이름의 마스코트가 있습니다.",
                    selections=[
                        Selection(
                            content="안뇽이",
                            correct=True,
                        ),
                        Selection(
                            content="김자바",
                            correct=False,
                        ),
                        Selection(
                            content="김코틀린",
                            correct=False,
                        ),
                        Selection(
                            content="김파이썬",
                            correct=False,
                        ),
                    ],
                ),
            ],
        )
