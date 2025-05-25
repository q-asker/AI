from fastapi import APIRouter, Depends  # 의존성 주입: 중복 제거에 효과적

# request, response에 대응
from app.dto.request.generate_request import GenerateRequest
from app.service.generate_service import GenerateService

router = APIRouter()


def get_generate_service():
    return GenerateService()


@router.post("/generate")
def generate(
        request: GenerateRequest,
        generate_service=Depends(get_generate_service)
):
    return generate_service.generate(request)
