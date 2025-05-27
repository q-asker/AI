from app.util.parsing import process_file
from app.dto.request.generate_request import GenerateRequest

import requests
import os
from dotenv import load_dotenv

load_dotenv()
aws_lambda_url = os.getenv("SUMMARY_AWS_LAMBDA_URL")

async def create_summary(text: str) -> str:
    try:
        summary = ""
        payload = {
            "bedrock_content": {
                "modelId": "us.anthropic.claude-sonnet-4-20250514-v1:0",
                "body": {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1024,
                    "system": "당신은 제공된 텍스트의 핵심 내용을 분석하여 200-300단어(words)로 간결하고 정확하게 요약하는 AI 전문가입니다.",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"다음 텍스트를 요약해주세요. 주요 개념, 핵심 아이디어, 중요한 정보를 명확히 포함해야 합니다. 이때 불필요한 설명이나 따옴표, 주석은 제외하세요.\n\n{text}"
                                }
                            ]
                        }
                    ]
                }
            }
        }

        response = requests.post(aws_lambda_url, json=payload)
        summary = response.json()["summary"]
        return summary
    except Exception as e:
        raise e