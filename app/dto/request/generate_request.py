from pydantic import BaseModel
from enum import Enum


class DOKLevel(str, Enum):
    RECALL = "RECALL"
    SKILLS = "SKILLS"
    STRATEGIC = "STRATEGIC"


class GenerateRequest(BaseModel):
    uploadedUrl: str
    quizCount: int
    difficultyType: DOKLevel
    quizType: str
