from enum import Enum
from typing import Optional

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
    pageSelected: bool
    startPageNumber: Optional[int]
    endPageNumber: Optional[int]
