from enum import Enum
from typing import List

from pydantic import BaseModel


class DOKLevel(str, Enum):
    RECALL = "RECALL"
    SKILLS = "SKILLS"
    STRATEGIC = "STRATEGIC"


class QuizType(str, Enum):
    OX = "OX"
    BLANK = "BLANK"
    MULTIPLE = "MULTIPLE"


class GenerateRequest(BaseModel):
    uploadedUrl: str
    quizCount: int
    difficultyType: DOKLevel
    quizType: QuizType
    pageNumbers: List[int]
