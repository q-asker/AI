import asyncio
import json
import os
from typing import List
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
    await asyncio.gather(*tasks, return_exceptions=True) # Redis에 요청 내용 저장


    if os.getenv("ENV") == "local":
        await process_on_local(keys, mcp_mode)
    elif os.getenv("ENV") == "remote":
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, process_on_remote, keys, mcp_mode) # SQS 사용
    else:
        raise ValueError("ENV must be either 'local' or 'remote'")

    return await collect_quizzes(baseKey, quiz_count)


async def collect_quizzes(baseKey, quiz_count) -> List[GeneratedResult]:
    seen_sequences = set()
    quizzes = []
    subscribe_key = "notify:" + baseKey
    try:
        async with asyncio.timeout(time_out):
            pubsub = await redis_util.subscribe(subscribe_key) # 해당 baseKey 채널 구독, 결과 메세지 수신
            async for msg in pubsub.listen(): # 메세지 sqs에 저장 이후 수행
                logger.info(f"Received message: {msg}")
                if msg["type"] != "message":
                    continue
                response = msg["data"]
                response_json = json.loads(response)
                sequence = response_json.get("sequence")
                if sequence in seen_sequences:
                    logger.warning(f"Duplicate sequence detected: {sequence}")
                    continue

                seen_sequences.add(sequence)
                quizzes.append(
                    GeneratedResult(
                        **response_json,
                    )
                )
                if len(quizzes) >= quiz_count:
                    await pubsub.unsubscribe(subscribe_key)
                    break

    except asyncio.TimeoutError:
        await pubsub.unsubscribe(subscribe_key)
        raise TimeoutError

    except Exception as e:
        raise e

    return quizzes


async def process_on_local(keys, mcp_mode):
    payload = {"keys": keys, "mcp_mode": mcp_mode}
    async with httpx.AsyncClient() as client:
        response = await client.post(aws_lambda_url, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error(f"Lambda 호출 실패: {exc}")
            raise exc


def process_on_remote(keys, mcp_mode): # SQS 사용시 수행
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
            response = sqs.send_message_batch(QueueUrl=aws_mcp_sqs_url, Entries=entries) # mcp lambda 트리거 하기

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
