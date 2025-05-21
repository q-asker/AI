from pydantic import BaseModel


class Selection(BaseModel):
    content: str
    correct: bool
