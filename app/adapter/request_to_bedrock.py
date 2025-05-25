import asyncio
import os
from uuid import uuid4

import requests
from dotenv import load_dotenv

from app.util.redis_util import RedisUtil

load_dotenv()
aws_lambda_url = os.getenv("AWS_LAMBDA_URL")
time_out = int(os.getenv("TIME_OUT", 60))


async def request_to_bedrock(bedrock_contents):
    redis_util = RedisUtil()
    message_group_id = str(uuid4())

    keys = []
    quiz_count = len(bedrock_contents)
    for i in range(quiz_count):
        key = "prompt:" + message_group_id + ":" + str(i)
        keys.append(key)

    tasks = []

    for i, bedrock_content in enumerate(bedrock_contents):
        key = keys[i]
        tasks.append(redis_util.save_bedrock_content(key, bedrock_content))

    await asyncio.gather(*tasks, return_exceptions=True)

    for key in keys:
        payload = {"message_group_id": message_group_id, "key": key}
        requests.post(aws_lambda_url, json=payload)

    quizzes = []
    try:
        async with asyncio.timeout(time_out):
            pubsub = await redis_util.subscribe(message_group_id)
            count = 0
            async for msg in pubsub.listen():
                print(msg)
                if msg["type"] != "message":
                    continue
                count += 1
                quizzes.append(msg["data"])
                if count >= quiz_count:
                    await pubsub.unsubscribe(f"notify:{message_group_id}")
                    break

    except asyncio.TimeoutError:
        await pubsub.unsubscribe(f"notify:{message_group_id}")
        raise TimeoutError

    return quizzes
