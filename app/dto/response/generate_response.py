from typing import List

from pydantic import BaseModel

from app.dto.model.problem_set import Selection


class ProblemResponse(BaseModel):
    number: int
    title: str
    selections: List[Selection]
    explanation: str
    referencedPages: List[int]


class GenerateResponse(BaseModel):
    quiz: List[ProblemResponse]
