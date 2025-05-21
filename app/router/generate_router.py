from fastapi import APIRouter, Depends

from app.dto.request.generate_request import GenerateRequest
from app.service.generate_service import GenerateService

router = APIRouter()


def get_generate_service():
    return GenerateService()


@router.post("/generate")
def generate(request: GenerateRequest, generate_service=Depends(get_generate_service)):
    return generate_service.generate(request)
