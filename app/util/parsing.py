import os
from http.client import HTTPException
from typing import List

import fitz
import requests
from fastapi import HTTPException


def process_file(uploaded_url: str, page_numbers: List[int]) -> List[str]:
    try:
        response = requests.get(uploaded_url)
        file_content = response.content

        if uploaded_url.endswith(".pdf"):
            pdf_documents = fitz.open(stream=file_content, filetype="pdf")

            content_length = 0
            one_based_pages = [""]
            for pdf_document in pdf_documents:
                content_length += len(pdf_document.get_text())
                one_based_pages.append(pdf_document.get_text())
            pdf_documents.close()

            if content_length < int(os.environ["MIN_TEXT_LENGTH"]):
                raise HTTPException(
                    status_code=400,
                    detail="파일에 텍스트가 충분하지 않습니다. \n 파일을 연 뒤, 텍스트가 선택되는지 확인해주세요. \n 선택되지 않는다면 OCR 변환이 필요합니다.",
                )
            select_pages = [
                one_based_pages[i] for i in page_numbers if 0 < i < len(one_based_pages)
            ]

            return [""] + select_pages

        else:
            raise ValueError("지원하지 않는 파일 형식입니다.")
    except Exception as e:
        raise e
