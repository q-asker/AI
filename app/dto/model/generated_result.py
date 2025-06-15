from pydantic import BaseModel


class GeneratedResult(BaseModel):
    sequence: int
    generated_text: str
