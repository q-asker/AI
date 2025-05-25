from pydantic import BaseModel


class GenerateRequest(BaseModel):
    uploadedUrl: str
    quizCount: int
    type: str
