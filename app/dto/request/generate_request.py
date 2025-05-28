from pydantic import BaseModel


class GenerateRequest(BaseModel):
    uploaded_url: str
    quiz_count: int
    type: str
