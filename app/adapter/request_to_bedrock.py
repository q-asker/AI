import asyncio
import json
import os
from typing import List, Tuple, Optional
from uuid import uuid4

import boto3
import httpx
from dotenv import load_dotenv

from app.dto.model.generated_result import GeneratedResult
from app.util.logger import logger
from app.util.redis_util import RedisUtil

load_dotenv()
aws_region = os.getenv("AWS_REGION")
aws_lambda_url = os.getenv("AWS_LAMBDA_URL")
aws_sqs_url = os.getenv("AWS_SQS_URL")
aws_mcp_sqs_url = os.getenv("AWS_MCP_SQS_URL")
time_out = int(os.getenv("TIME_OUT"))

sqs = boto3.client("sqs", region_name=aws_region)
redis_util = RedisUtil()


async def request_to_bedrock(bedrock_contents, mcp_mode=False):
    keys = []
    quiz_count = len(bedrock_contents)

    baseKey = str(uuid4())
    for i in range(quiz_count):
        key = "prompt:" + baseKey + ":" + str(i)
        keys.append(key)

    tasks = []
    for i, bedrock_content in enumerate(bedrock_contents):
        key = keys[i]
        tasks.append(redis_util.save_bedrock_content(key, bedrock_content))
    await asyncio.gather(*tasks, return_exceptions=True)  # Redis에 요청 내용 저장

    if os.getenv("ENV") == "local":
        await process_on_local(keys, mcp_mode)
    elif os.getenv("ENV") == "remote":
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, process_on_remote, keys, mcp_mode)  # SQS 사용
    else:
        raise ValueError("ENV must be either 'local' or 'remote'")

    return await collect_quizzes(baseKey, quiz_count)


async def collect_quizzes(baseKey, quiz_count) -> List[GeneratedResult]:
    seen_sequences = set()
    published_count = 0
    quizzes = []
    subscribe_key = "notify:" + baseKey
    pubsub = None
    try:
        async with asyncio.timeout(time_out):
            pubsub = await redis_util.subscribe(subscribe_key)

            # 코루틴 일시정지, 메시지가 오면 다시 스케쥴링됨
            async for msg in pubsub.listen():
                published_count += 1
                status, result = try_make_generated_result(msg, seen_sequences)
                if status is "ok":
                    quizzes.append(result)
                if published_count == quiz_count:
                    break

    except asyncio.TimeoutError:
        raise TimeoutError

    except Exception as e:
        raise e

    finally:
        if pubsub is not None:
            await pubsub.unsubscribe(subscribe_key)

    return quizzes


def try_make_generated_result(
    msg, seen_sequences
) -> Tuple[str, Optional[GeneratedResult]]:
    logger.info(f"Received message: {msg}")
    if msg["type"] != "message":
        return "fail", None

    response = msg["data"]

    try:
        response_json = json.loads(response)
    except json.JSONDecodeError:
        return "fail", None

    sequence = response_json.get("sequence")
    if sequence in seen_sequences:
        logger.warning(f"Duplicate sequence detected: {sequence}")
        return "fail", None

    seen_sequences.add(sequence)
    return "ok", GeneratedResult(
        **response_json,
    )


async def process_on_local(keys, mcp_mode):
    payload = {"keys": keys, "mcp_mode": mcp_mode}
    async with httpx.AsyncClient() as client:
        response = await client.post(aws_lambda_url, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error(f"Lambda 호출 실패: {exc}")
            raise exc


def process_on_remote(keys, mcp_mode):  # SQS 사용시 수행
    message_group_id = keys[0].split(":")[1]
    for i in range(0, len(keys), 10):
        if mcp_mode:
            entries = []
            batch = keys[i : i + 10]
            for j, key in enumerate(batch):
                entries.append(
                    {
                        "Id": str(j),
                        "MessageBody": key,
                        "MessageGroupId": message_group_id,
                    }
                )
            response = sqs.send_message_batch(QueueUrl=aws_mcp_sqs_url, Entries=entries)

        else:
            entries = []
            batch = keys[i : i + 10]
            for j, key in enumerate(batch):
                entries.append(
                    {
                        "Id": str(j),
                        "MessageBody": key,
                    }
                )
            response = sqs.send_message_batch(QueueUrl=aws_sqs_url, Entries=entries)

        if response.get("Failed"):
            raise Exception("Failed to send messages to SQS")
        else:
            logger.info(f"Batch of {len(entries)} messages sent.")
