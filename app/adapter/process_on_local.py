import os

import httpx
from dotenv import load_dotenv

from app.util.logger import logger

load_dotenv()
aws_lambda_url = os.getenv("AWS_LAMBDA_URL")


async def process_on_local(keys, mcp_mode):
    payload = {"keys": keys, "mcp_mode": mcp_mode}
    async with httpx.AsyncClient() as client:
        response = await client.post(aws_lambda_url, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error(f"Lambda 호출 실패: {exc}")
            raise exc
