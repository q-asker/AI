from pydantic import BaseModel

from app.dto.model.problem import Problem


class SubProblemSet(BaseModel):
    quiz: list[Problem]
