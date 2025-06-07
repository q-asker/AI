from enum import Enum

from pydantic import BaseModel


class DOKLevel(str, Enum):
    RECALL = "RECALL"
    SKILLS = "SKILLS"
    STRATEGIC = "STRATEGIC"


class GenerateRequest(BaseModel):
    uploadedUrl: str
    quizCount: int
    difficultyType: DOKLevel
    quizType: str
    selectedPages: list[int]
