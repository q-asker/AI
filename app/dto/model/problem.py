from pydantic import BaseModel

from app.dto.model.selection import Selection


class Problem(BaseModel):
    number: int
    title: str
    selections: list[Selection]
    explanation: str
    
