from pydantic import BaseModel
from typing import List


class Selection(BaseModel):
    content: str
    correct: bool

class Problem(BaseModel):
    number: int
    title: str
    selections: List[Selection]
    explanation: str

class GenerateResponse(BaseModel):
    title: str
    quiz: List[Problem]
