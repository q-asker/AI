import os

from openai import AsyncOpenAI

_gpt_client: AsyncOpenAI | None = None


def get_gpt_client() -> AsyncOpenAI:
    """OpenAI 비동기 클라이언트를 싱글톤으로 제공한다."""
    global _gpt_client
    if _gpt_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다.")

        _gpt_client = AsyncOpenAI(api_key=api_key, max_retries=0)

    return _gpt_client
