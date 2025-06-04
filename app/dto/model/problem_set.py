from typing import List

from pydantic import BaseModel, Field


class Selection(BaseModel):
    content: str = Field(description="선택지 내용입니다.")
    correct: bool = Field(
        description="정답 여부입니다. 정답이면 True, 오답이면 False입니다."
    )


class Problem(BaseModel):
    number: int = Field(description="문제 번호입니다.")
    title: str = Field(description="문제 내용입니다.")
    selections: List[Selection] = Field(description="선택지 목록입니다.")
    explanation: str = Field(description="문제에 대한 해설입니다.")


class ProblemSet(BaseModel):
    quiz: List[Problem] = Field(description="퀴즈 목록입니다.")
