from fastapi import APIRouter, Depends

from app.dto.request.generate_request import GenerateRequest
from app.dto.request.specific_explanation_request import SpecificExplanationRequest
from app.dto.response.generate_response import GenerateResponse
from app.dto.response.specific_explanation_response import SpecificExplanationResponse
from app.service.explanation_service import ExplanationService
from app.service.generate_service import GenerateService

router = APIRouter()


def get_generate_service():
    return GenerateService()


def get_explanation_service():
    return ExplanationService()


@router.post("/generation")
async def generate(
    request: GenerateRequest, generate_service=Depends(get_generate_service)
) -> GenerateResponse:
    return await generate_service.generate(request)


@router.post("/specific-explanation")
async def generate_specific_explanation(
    request: SpecificExplanationRequest,
    explanation_service=Depends(get_explanation_service),
) -> SpecificExplanationResponse:
    return await explanation_service.generate_specific_explanation(request)
