from app.adapter.request_generate_specific_explanation_to_gpt import (
    request_specific_explanation,
)
from app.adapter.request_search_references_to_gpt import request_search_references
from app.dto.request.search_request import SearchRequest
from app.dto.request.specific_explanation_request import SpecificExplanationRequest
from app.dto.response.specific_explanation_response import SpecificExplanationResponse
from app.util.logger import logger
from app.util.timing import log_elapsed


class ExplanationService:
    @staticmethod
    async def generate_specific_explanation(
        specific_explanation_request: SpecificExplanationRequest,
    ):
        title = specific_explanation_request.title
        selections = specific_explanation_request.selections

        selection_text = ""
        for idx, s in enumerate(selections, start=1):
            answer_tag = "(정답)" if s.correct else ""
            selection_text += f"{idx}. {s.content} {answer_tag}\n"

        gpt_contents = [
            {
                "model": "gpt-5-mini",
                "temperature": 0.2,
                "max_completion_tokens": 2000,
                "messages": [
                    {
                        "role": "system",
                        "content": "\n".join(
                            [
                                "아래는 하나의 객관식 문제와 4개의 선택지입니다. 각 선택지는 정답 여부도 함께 제공됩니다.",
                                "문제를 바탕으로, 왜 해당 정답이 맞는지, 다른 선택지들은 왜 틀렸는지를 논리적으로 설명하세요.",
                                "- JSON이 아닌 단순 서술문으로 답하세요.",
                                "- 하나의 글로 작성하세요.",
                            ]
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"문제: {title}\n\n선택지:\n{selection_text}",
                    },
                ],
            }
        ]

        with log_elapsed(logger, "request_specific_explanation"):
            generated_result = await request_specific_explanation(gpt_contents)

        explanation_text = generated_result[0].generated_text if generated_result else ""

        return SpecificExplanationResponse(specific_explanation=explanation_text)

    @staticmethod
    async def search_and_generate(search_request: SearchRequest):
        query = search_request.query
        response_schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "references": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                            "why": {"type": "string"},
                        },
                        "required": ["title", "url", "why"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["references"],
            "additionalProperties": False,
        }

        gpt_content = {
            "model": "gpt-5-mini",
            "temperature": 0.2,
            "max_completion_tokens": 1200,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "search_references", "strict": True, "schema": response_schema},
            },
            "messages": [
                {
                    "role": "system",
                    "content": "\n".join(
                        [
                            "사용자의 질의에 대해 학습에 도움이 되는 참고 링크를 추천한다.",
                            "가능하면 공식 문서/표준/신뢰할 수 있는 자료를 우선한다.",
                            "반드시 JSON 스키마에 맞춰서만 출력한다.",
                        ]
                    ),
                },
                {"role": "user", "content": f"질의: {query}\n\n참고 사이트(3~6개)를 추천해줘."},
            ],
        }

        with log_elapsed(logger, "request_search_references"):
            result = request_search_references(gpt_content)

        return result

