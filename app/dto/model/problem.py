from pydantic import BaseModel
from pydantic import Field

from app.dto.model.selection import Selection


class Problem(BaseModel):
    title: str = Field(
        default="",
        description="문제의 제목입니다.",
    )

    explanation: str = Field(
        default="",
        description="문제의 해설입니다",
    )

    selections: list[Selection]
