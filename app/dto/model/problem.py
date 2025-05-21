from pydantic import BaseModel

from app.dto.model.selection import Selection


class Problem(BaseModel):
    title: str
    explanation: str
    selections: list[Selection]
