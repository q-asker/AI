from pydantic import BaseModel

from app.dto.model.problem import Problem


class GenerateResponse(BaseModel):
    title: str
    problems: list[Problem]
