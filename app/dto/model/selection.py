from pydantic import BaseModel
from pydantic import Field


class Selection(BaseModel):
    content: str = Field(
        default="",
        description="선택지의 내용입니다",
    )
    correct: bool = Field(
        default="",
        description="정답 여부입니다. True면 정답, False면 오답입니다.",
    )
