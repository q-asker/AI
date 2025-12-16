import asyncio

from app.adapter.request_single import request_responses_output_text
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

        # 단일 Responses API 호출에서 웹 검색 + 해설 생성을 함께 수행한다.
        messages = [
            {
                "role": "system",
                "content": "\n".join(
                    [
                        "너는 학습을 돕는 튜터다.",
                        "필요하면 웹 검색 도구를 사용해 신뢰할 수 있는 참고문서를 찾고, 그 근거를 바탕으로 해설을 작성한다.",
                        "반드시 사람이 읽을 수 있는 텍스트로만 출력한다(어떤 JSON 구조도 금지).",
                        "출력 형식:",
                        "1) 참고문서(3~6개): 각 항목은 제목/URL/이유를 포함",
                        "2) 상세 해설: 왜 정답이 맞는지, 오답이 왜 틀렸는지 논리적으로 한 글로 설명",
                        "참고문서에 없는 URL/출처를 새로 만들어내지 마라.",
                    ]
                ),
            },
            {
                "role": "user",
                "content": "\n".join(
                    [
                        f"문제: {title}",
                        "",
                        "선택지(정답 표시 포함):",
                        selection_text.strip(),
                    ]
                ),
            },
        ]

        gpt_content = {
            "model": "gpt-5-mini",
            "max_output_tokens": 2200,
            "input": messages,
            "tools": [{"type": "web_search_preview"}],
            "tool_choice": "auto",
        }

        with log_elapsed(logger, "request_specific_explanation_with_search"):
            combined_text = await asyncio.to_thread(request_responses_output_text, gpt_content)
            combined_text = (combined_text or "").strip()

        references = []
        return SpecificExplanationResponse(
            specific_explanation=combined_text, references=references
        )
