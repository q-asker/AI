from typing import List

from pydantic import BaseModel, Field


class Reference(BaseModel):
    title: str
    url: str
    why: str


class SpecificExplanationResponse(BaseModel):
    specific_explanation: str
    references: List[Reference] = Field(default_factory=list)
