from app.adapter.request_single import request_responses_output_text_async
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
                        "너는 학습을 돕는 튜터다. 주어진 문제와 선택지들을 해설해준다.",
                        "필요하면 웹 검색 도구를 사용해 신뢰할 수 있는 참고문서를 찾고, 그 근거를 바탕으로 해설을 작성한다.",
                        "### 제약 사항",
                        "원한다면, 더 도와드리겠다는 말 출력 금지. 해설 작성에 집중",
                        "### 출력 형식:",
                        "상세 해설: 왜 정답이 맞는지, 오답이 왜 틀렸는지 논리적으로 한 글로 설명, 참고하면 좋은 URL 제시",
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
            "max_output_tokens": 10000,
            "input": messages,
            "tools": [{"type": "web_search_preview"}],
            "tool_choice": "auto",
        }

        with log_elapsed(logger, "request_specific_explanation_with_search"):
            combined_text = await request_responses_output_text_async(
                gpt_content, timeout=60
            )
            combined_text = (combined_text or "").strip()

        references = []
        return SpecificExplanationResponse(
            specific_explanation=combined_text, references=references
        )
