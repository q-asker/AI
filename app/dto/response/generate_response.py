from pydantic import BaseModel
from pydantic import Field

from app.dto.model.problem import Problem


class GenerateResponse(BaseModel):
    title: str = Field(
        default="",
        description="문제집의 제목입니다.",
    )
    problems: list[Problem]
