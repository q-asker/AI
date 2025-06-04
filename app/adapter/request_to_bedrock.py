import asyncio
import os
from uuid import uuid4

import boto3
import requests
from dotenv import load_dotenv

from app.util.logger import logger
from app.util.redis_util import RedisUtil

load_dotenv()
aws_region = os.getenv("AWS_REGION")
aws_lambda_url = os.getenv("AWS_LAMBDA_URL")
aws_sqs_url = os.getenv("AWS_SQS_URL")
time_out = int(os.getenv("TIME_OUT", 120))


sqs = boto3.client("sqs", region_name=aws_region)


async def request_to_bedrock(bedrock_contents):
    redis_util = RedisUtil()
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
    await asyncio.gather(*tasks, return_exceptions=True)

    if os.getenv("ENV") == "local":
        process_on_local(keys)
    elif os.getenv("ENV") == "remote":
        process_on_remote(keys)
    else:
        raise ValueError("ENV must be either 'local' or 'remote'")

    quizzes = []
    subscribe_key = "notify:" + baseKey
    try:
        async with asyncio.timeout(time_out):
            pubsub = await redis_util.subscribe(subscribe_key)
            count = 0
            async for msg in pubsub.listen():
                logger.info(f"Received message: {msg}")
                if msg["type"] != "message":
                    continue
                count += 1
                quizzes.append(msg["data"])
                if count >= quiz_count:
                    await pubsub.unsubscribe(subscribe_key)
                    break

    except asyncio.TimeoutError:
        await pubsub.unsubscribe(subscribe_key)
        raise TimeoutError

    return quizzes


def process_on_local(keys):
    payload = {"keys": keys}
    requests.post(aws_lambda_url, json=payload)


def process_on_remote(keys):
    message_group_id = str(uuid4())
    for i in range(0, len(keys), 10):
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
        response = sqs.send_message_batch(QueueUrl=aws_sqs_url, Entries=entries)
        if response.get("Failed"):
            raise Exception("Failed to send messages to SQS")
        else:
            logger.info(f"Batch of {len(entries)} messages sent successfully.")
