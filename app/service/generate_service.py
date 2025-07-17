import json
import time
from typing import List

from langchain_core.output_parsers import JsonOutputParser

from app.adapter.request_to_bedrock import request_to_bedrock
from app.dto.model.problem_set import ProblemSet
from app.dto.request.generate_request import GenerateRequest, QuizType
from app.dto.request.search_request import SearchRequest
from app.dto.response.generate_response import (
    GenerateResponse,
    ProblemResponse,
)
from app.util.create_chunks import create_chunks
from app.util.logger import logger
from app.util.parsing import process_file
from app.util.redis_util import RedisUtil

redis_util = RedisUtil()


class GenerateService:

    @staticmethod
    async def search_and_generate(search_request: SearchRequest):
        query = search_request.query
        bedrock_contents = [
            {
                "modelId": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                "body": {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 5000,
                    "system": f"""
                            주어지는 내용을 바탕으로 적절한 참고 사이트를 찾아주세요""",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"""
                                        ${query}
                                        """,
                                }
                            ],
                        }
                    ],
                },
            }
        ]

        await redis_util.check_bedrock_rate(len(bedrock_contents), "rl:bedrock:global")

        start = time.time()
        generated_result = await request_to_bedrock(bedrock_contents, mcp_mode=True)
        end = time.time()
        elapsed = end - start
        logger.info(f"소요 시간: {elapsed:.4f}초")
        return json.loads(generated_result[0])

    @staticmethod
    async def generate(generate_request: GenerateRequest):
        uploaded_url = generate_request.uploadedUrl
        total_quiz_count = generate_request.quizCount
        dok_level = generate_request.difficultyType
        quiz_type = generate_request.quizType
        page_numbers = generate_request.pageNumbers

        texts = process_file(
            uploaded_url, page_numbers
        )

        minimum_page_text_length_per_chunk = 500
        max_chunk_count = 25
        chunks = create_chunks(
            texts, total_quiz_count, minimum_page_text_length_per_chunk, max_chunk_count
        )

        await redis_util.check_bedrock_rate(len(chunks), "rl:bedrock:global")

        for chunk in chunks:
            chunk.referenced_pages = [
                page_numbers[i - 1]
                for i in chunk.referenced_pages
                if 1 <= i <= len(page_numbers)
            ]

        parser = JsonOutputParser(pydantic_object=ProblemSet)
        format_instructions = parser.get_format_instructions()

        bedrock_contents = []
        for chunk in chunks:
            bedrock_contents.append(
                {
                    "modelId": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                    "body": {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 5000,
                        "system": f"""
                        주어진 강의노트 내용을 분석하여 학생들의 이해도를 평가할 수 있는 효과적인 퀴즈 {chunk.quiz_count}개를 생성해주세요.
                        문제 생성 지침:
                        {get_dok_system_prompt(dok_level, quiz_type)}

                        응답 요구사항:
                        - 한국어로 작성
                        - JSON 형식으로만 출력 (다른 텍스트 포함 금지)
                        - 강의노트의 핵심 개념을 다루는 문제
                        - 학습 목표와 연결된 평가 문항
                        {get_quiz_format_instruction(quiz_type)}
                        JSON 구조:
                        {format_instructions}""",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"""
                                                    # 강의노트
                                                    {chunk.text}
                                                """,
                                    }
                                ],
                            }
                        ],
                    },
                }
            )

        start = time.time()
        generated_results = await request_to_bedrock(bedrock_contents)
        end = time.time()
        elapsed = end - start
        logger.info(f"소요 시간: {elapsed:.4f}초")

        sorted_responses = []
        for i, generated_result in enumerate(generated_results):
            try:
                generated_text = parser.parse(generated_result.generated_text)
                sorted_responses.append(
                    {
                        "sequence": generated_result.sequence,
                        "generated_text": generated_text,
                    }
                )
            except Exception as e:
                logger.error(f"Parsing error for response {i}: {e}")
                logger.error(f"Response content: {generated_result.generated_text}")
                continue

        sorted_responses.sort(key=lambda x: x["sequence"])

        problem_responses: List[ProblemResponse] = []
        for i, generated_result in enumerate(sorted_responses):
            quiz_data = generated_result.get("generated_text")
            quiz = quiz_data.get("quiz")
            for problem in quiz:
                problem_responses.append(
                    ProblemResponse(
                        **problem, referencedPages=chunks[i].referenced_pages
                    )
                )

        for i, problem in enumerate(problem_responses):
            problem.number = i + 1

        return GenerateResponse(quiz=problem_responses)
    
def get_quiz_format_instruction(quiz_type: QuizType):
    if quiz_type == QuizType.OX:
        return """
        - OX 문제로 생성 (참/거짓 문제)
        - 선택지는 "O (참)" 과 "X (거짓)" 2개만 제공
        - 정답은 O 또는 X 중 하나로 설정
        """
    else:  # QuizType.MULTIPLE
        return """
        - 객관식 문제로, 4개의 선택지 제공
        - 정답은 하나로 설정, 1~4번 중 무작위로 배치
        """


def get_dok_system_prompt(dok_level: str, quiz_type: QuizType):
    if quiz_type == QuizType.OX:
        ox_guidelines = {
            "RECALL": """
            **DOK Level 1 - 기억/재생산 (RECALL) OX 문제 생성 지침:**

            **필수 조건:**
            - 기본 개념, 정의, 용어의 참/거짓을 판단하는 문제
            - 단순 암기 내용의 정확성을 확인
            - 명확하게 참 또는 거짓으로 판단 가능한 진술
            - **미묘한 차이**: 비슷해 보이지만 세부 사항에서 참/거짓이 갈리는 문제

            **적절한 문제 예시:**
            - "리액트는 페이스북에서 개발한 자바스크립트 프레임워크이다." (X - 라이브러리임)
            - "파이썬에서 변수 선언 시 타입을 명시적으로 지정해야 한다." (X - 동적 타이핑)
            - "HTML의 <span> 태그는 기본적으로 인라인 레벨 요소이다." (O)
            """,
            "SKILLS": """
            **DOK Level 2 - 기술과 개념 (SKILLS) OX 문제 생성 지침:**

            **필수 조건:**
            - 개념 적용과 관계 이해를 평가하는 참/거짓 문제
            - 상황별 적절성과 인과관계의 참/거짓 판단
            - 코드 동작이나 결과에 대한 참/거짓 문제
            - **미묘한 구분**: 조건이나 상황에 따라 결과가 달라지는 케이스

            **적절한 문제 예시:**
            - "useState Hook을 사용할 때 초기값이 함수인 경우 매 렌더링마다 해당 함수가 실행된다." (X - 초기 렌더링시만)
            - "CSS에서 position: absolute는 항상 가장 가까운 positioned 부모 요소를 기준으로 위치가 결정된다." (O)
            - "자바스크립트에서 호이스팅은 var 선언과 function 선언 모두에 동일하게 적용된다." (X - 동작 방식이 다름)
            """,
            "STRATEGIC": """
            **DOK Level 3 - 전략적 사고 (STRATEGIC) OX 문제 생성 지침:**

            **필수 조건:**
            - 복합적 상황과 전략적 판단의 참/거짓을 평가
            - 설계 원칙, 최적화 전략, 아키텍처 결정의 적절성 판단
            - 여러 요소를 종합한 결론의 참/거짓 문제
            - **고차원적 사고**: 업계 베스트 프랙티스, 트레이드오프, 복합적 시나리오

            **다양한 분야별 고차원적 문제 예시:**
            
            - "마케팅에서 개인화 알고리즘을 통한 타겟팅 정확도 향상은 고객 만족도를 높이지만 프라이버시 침해 우려와 필터 버블 현상을 야기할 수 있다." (O - 개인화의 양면성)
            - "조직 심리학에서 수평적 의사결정 구조는 구성원의 참여도와 창의성을 높이지만 의사결정 속도 저하와 책임 소재 불분명 문제를 동반한다." (O - 수평적 구조의 트레이드오프)
            - "교육 공학에서 적응형 학습 시스템은 개별 학습자의 속도에 맞춘 맞춤형 교육을 제공하여 학습 효과를 극대화하면서도 사회적 학습 기회를 감소시킬 위험이 있다." (O - 개별화 vs 사회적 학습)
            - "경제학에서 행동경제학적 넛지 기법을 정책에 적용하면 시민의 자율성을 존중하면서도 사회적 후생을 증진시킬 수 있다." (O - 넛지의 효과와 윤리적 고려)
            - "소프트웨어 공학에서 마이크로서비스 아키텍처는 시스템의 확장성과 유지보수성을 향상시키지만 네트워크 복잡도와 운영 오버헤드를 증가시킨다." (O - 마이크로서비스의 트레이드오프)
            """
        }
        
        ox_instruction = ox_guidelines.get(dok_level, ox_guidelines["RECALL"])
        
        return (
            ox_instruction + 
            "\n\n**OX 문제 생성 핵심 규칙:**\n"
            "1. **그럴듯함**: 둘 다 전문가가 말할 법한 그럴듯한 내용으로 구성\n"
            "2. **미묘한 차이**: 전문 지식이 있어야만 구분할 수 있는 섬세한 차이점 활용\n"
            "3. **함정 요소**: 일반적인 오해나 혼동하기 쉬운 개념을 적절히 활용\n"
            "4. **맥락 의존**: 특정 조건이나 상황에서만 참/거짓이 결정되는 문제\n"
            "5. **정확성**: 강의노트 내용을 바탕으로 한 정확한 사실 관계 확인\n"
            "6. **적절한 난이도**: 너무 명백하지도, 불가능하지도 않은 적정 수준 유지\n"
        )
    else:  # QuizType.MULTIPLE
        dok_guidelines = {
            "RECALL": """
            **DOK Level 1 - 기억/재생산 (RECALL) 문제 생성 지침:**

            **필수 조건:**
            - 순수한 기억과 암기만을 평가하는 문제
            - 정의, 용어, 메소드명, 개념명 등의 단순 재생산
            - 계산이나 코드 작성, 적용 과정이 필요하지 않은 문제
            - 학습한 내용을 있는 그대로 기억하는지만 확인
            - **빈칸 채우기 형태로 문제를 생성** (핵심 개념을 _______로 표시)

            **금지 사항:**
            - 코드 작성이나 수정을 요구하는 문제
            - 여러 단계의 사고 과정이 필요한 문제
            - 개념을 새로운 상황에 적용하는 문제
            - 비교, 분석, 추론이 필요한 문제

            **적절한 문제:**
            - "_______ 는 객체지향 프로그래밍의 핵심 특징 중 하나이다."
            - "리액트에서 상태 관리를 위해 사용하는 Hook은 _______이다."
            - "데이터베이스의 _______ 는 테이블 간의 관계를 정의한다."
            - "자바스크립트에서 _______ 는 비동기 처리를 위한 객체이다."

            **선택지 구성:**
            - 정답 1개와 명확히 구분되는 오답 3개
            - 비슷한 용어나 개념으로 혼동을 유발하는 오답
            - 빈칸에 들어갈 수 있는 핵심 개념들로 구성
                        """,
            "SKILLS": """

            **DOK Level 2 - 기술과 개념 (SKILLS) 문제 생성 지침:**
            **필수 조건:**
            - 개념의 적용, 비교, 분류, 분석을 요구하는 문제
            - 학습한 내용을 새로운 맥락이나 상황에 적용
            - 원인과 결과 관계, 패턴 인식, 관계 파악
            - 2-3단계의 사고 과정이 필요한 문제

            **평가 요소:**
            - 개념 이해 및 적용 능력
            - 상황 분석 및 적절한 해결 방법 선택
            - 코드 해석 및 결과 예측
            - 비교 분석 및 분류 능력

            **적절한 문제:**
            - "다음 상황에서 가장 적절한 방법은?"
            - "주어진 코드의 실행 결과는?"
            - "○○와 ○○의 차이점은?"
            - "이 문제를 해결하기 위해 사용해야 할 컴포넌트는?"

            **선택지 구성:**
            - 모두 그럴듯해 보이지만 상황에 따른 적절성이 다른 선택지
            - 개념 이해도에 따라 구분되는 선택지
                        """,
            "STRATEGIC": """
            **DOK Level 3 - 전략적 사고 (STRATEGIC) 문제 생성 지침:**

            **필수 조건:**
            - 복잡한 문제 상황의 분석 및 평가
            - 다양한 관점에서의 해석과 논리적 판단
            - 증거를 바탕으로 한 추론 및 결론 도출
            - 전략적 접근과 창의적 문제 해결

            **평가 요소:**
            - 복합적 상황 분석 능력
            - 논리적 추론 및 판단 능력
            - 최적의 해결책 도출 능력
            - 다양한 요소를 종합한 의사결정 능력

            **적절한 문제:**
            - "다음 시스템 설계에서 가장 중요하게 고려해야 할 요소는?"
            - "주어진 요구사항을 만족하는 최적의 아키텍처는?"
            - "이 문제 상황을 해결하기 위한 가장 효과적인 전략은?"
            - "주어진 제약 조건에서 최선의 선택은?"

            **선택지 구성:**
            - 모두 타당성이 있어 보이는 고수준의 선택지
            - 깊은 분석과 종합적 판단을 통해서만 구분 가능
            - 복합적 고려 사항이 반영된 선택지
            """,
        }

        dok_instruction = dok_guidelines.get(dok_level, dok_guidelines["RECALL"])

        return (
            dok_instruction
            + "\n\n**중요:** 반드시 해당 DOK 레벨의 조건을 엄격히 준수하세요."
        )
