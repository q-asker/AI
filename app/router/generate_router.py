from fastapi import APIRouter
from starlette.responses import StreamingResponse

from app.dto.request.generate_request import GenerateRequest
from app.dto.request.specific_explanation_request import SpecificExplanationRequest
from app.dto.response.specific_explanation_response import SpecificExplanationResponse
from app.service.explanation_service import ExplanationService
from app.service.generate_service import GenerateService

router = APIRouter()


@router.post("/generation")
async def generate(request: GenerateRequest) -> StreamingResponse:
    return StreamingResponse(
        GenerateService.generate(request), media_type="application/x-ndjson"
    )


@router.post("/specific-explanation")
async def generate_specific_explanation(
    request: SpecificExplanationRequest,
) -> SpecificExplanationResponse:
    return await ExplanationService.generate_specific_explanation(request)
