from fastapi import APIRouter, Depends

from app.dto.request.generate_request import GenerateRequest
from app.dto.request.search_request import SearchRequest
from app.dto.response.generate_response import GenerateResponse
from app.service.generate_service import GenerateService
from app.dto.request.specific_explanation_request import SpecificExplanationRequest

router = APIRouter()


def get_generate_service():
    return GenerateService()


@router.post("/generation")
async def generate(
    request: GenerateRequest, generate_service=Depends(get_generate_service)
) -> GenerateResponse:
    return await generate_service.generate(request)


@router.post("/generation/search")
async def generate(
    request: SearchRequest, generate_service=Depends(get_generate_service)
):
    return await generate_service.search_and_generate(request)

@router.post("/specific-explanation")
async def generate_specific_explanation(
    request: SpecificExplanationRequest, generate_service=Depends(get_generate_service)
):
    return await generate_service.generate_specific_explanation(request)