from pydantic import BaseModel
from typing import List
from app.dto.model.problem_set import Selection


class SpecificExplanationRequest(BaseModel):
    title: str
    selections: List[Selection]
