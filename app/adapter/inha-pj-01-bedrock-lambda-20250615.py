import dotenv
import asyncio
import json
import logging

import boto3
import redis
from botocore.exceptions import ClientError
from openai import OpenAI  # OpenAI SDK

dotenv.load_dotenv()

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Redis 설정
redis_client = redis.Redis(
    host="redis.q-asker.com",
    port=6379,
    db=0,
    password="inha-cc-01",
    decode_responses=True,
)

# GPT 클라이언트 (환경변수 OPENAI_API_KEY 사용)
gpt_client = OpenAI(
    api_key=None  # 환경변수 OPENAI_API_KEY 사용
)

# SQS 설정
sqs = boto3.client("sqs")
QUEUE_URL =


def extract_json(raw: str) -> str:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return raw[start : end + 1]


def call_gpt_(gpt_content: dict) -> str:
    """
    Redis에 저장된 gpt_content를 기반으로 GPT API 호출
    예상 gpt_content 구조:

    {
        "model": "gpt-5-nano",
        "temperature": 0.2,
        "max_completion_tokens": 4000,
        "messages": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."}
        ]
    }

    또는 fallback 용으로 body.prompt / body.inputText 를 사용할 수 있음.
    """
    # 기본 모델 (없으면 gpt-5-nano 사용)
    model = gpt_content.get("model") or "gpt-5-nano"

    # messages가 있으면 그대로 사용
    messages = gpt_content.get("messages")
    if not messages:
        # 기존 Bedrock body 구조를 최대한 재사용
        body = gpt_content.get("body") or {}
        prompt = (
            body.get("prompt")
            or body.get("inputText")
            or json.dumps(body, ensure_ascii=False)
        )
        messages = [{"role": "user", "content": prompt}]

    try:
        # 옵션 파라미터 구성
        kwargs = {
            "model": model,
            "messages": messages,
        }

        temperature = gpt_content.get("temperature")
        if temperature is not None:
            kwargs["temperature"] = temperature

        max_completion_tokens = gpt_content.get("max_completion_tokens")
        if max_completion_tokens is not None:
            kwargs["max_completion_tokens"] = max_completion_tokens

        # 필요하면 timeout도 설정 가능 (예: timeout=30)
        resp = gpt_client.chat.completions.create(**kwargs)
        print(resp)
        return resp.choices[0].message.content
    except Exception:
        logger.exception("GPT 호출 실패")
        return "fail"


def run_by_each_record(record):
    key = record["body"]
    logger.info(f"Processing key: {key}")
    recv_count = int(record.get("attributes", {}).get("ApproximateReceiveCount", "1"))

    # Redis에서 GPT 요청 정보 가져오기
    raw = redis_client.get(key)
    logger.info(f"Redis raw: {raw}")

    if raw is None:
        logger.warning(f"[{key}] Redis에 데이터가 없습니다.")
        generated_text = "fail"
    else:
        try:
            gpt_content = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"[{key}] Redis JSON 파싱 실패 ({e.msg})")
            generated_text = "fail"
        else:
            generated_text = call_gpt_(gpt_content)

    # JSON 파싱 시도 (결과가 올바른 JSON인지 확인)
    try:
        extracted_json = extract_json(generated_text)
        json.loads(extracted_json)
    except json.JSONDecodeError as e:
        logger.error(
            f"[{key}] 응답 JSON 파싱 실패 ({e.msg}), receive count={recv_count}"
        )
        if recv_count == 1:
            try:
                # 메시지 가시성 타임아웃을 0으로 설정하여 즉시 재노출
                receipt_handle = record.get("receiptHandle")
                sqs.change_message_visibility(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=receipt_handle,
                    VisibilityTimeout=0,
                )
                logger.info(
                    f"[{key}] ChangeMessageVisibility 호출로 메시지 가시성 재노출"
                )
                return
            except ClientError as vis_err:
                logger.error(f"[{key}] ChangeMessageVisibility 중 오류: {vis_err}")
        else:
            logger.warning(f"[{key}] 이미 1회 재시도 후 실패, 더 이상 처리하지 않음")
        generated_text = "fail"

    # 처리 결과를 Redis Pub/Sub으로 발행
    try:
        message_group_id = key.split(":")[1]
        sequence = key.split(":")[2]
        response = {"sequence": sequence, "generated_text": generated_text}
        redis_client.publish(
            f"notify:{message_group_id}", json.dumps(response, ensure_ascii=False)
        )
        logger.info(f"[{key}] 결과 publish 완료")
    except Exception as e:
        logger.exception(f"[{key}] 후속 처리 중 오류: {e}")


async def run_tasks(records):
    tasks = [asyncio.to_thread(run_by_each_record, rec) for rec in records]
    await asyncio.gather(*tasks)


def lambda_handler(event, context):
    records = event.get("Records", [])
    asyncio.run(run_tasks(records))
    # 부분 실패 처리하려면 여기서 batchItemFailures 채워주면 됨
    return {"batchItemFailures": []}
