from pydantic import BaseModel


class GenerateRequest(BaseModel):
    file_url: str
    quiz_count: int
