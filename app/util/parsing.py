import os
import tempfile
from typing import List

import fitz  # PyMuPDF
import requests
from pptx import Presentation


def process_file(uploaded_url: str, selected_pages: List[int]) -> List[str]:
    try:
        response = requests.get(uploaded_url)
        file_content = response.content

        if uploaded_url.endswith(".pdf"):
            pdf_documents = fitz.open(stream=file_content, filetype="pdf")
            pages = []
            pages
            for pdf_document in pdf_documents:
                pages.append(pdf_document.get_text())

            pdf_documents.close()

            return pages

        elif uploaded_url.endswith(".pptx"):
            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name

            presentation = Presentation(temp_file_path)
            pages = []
            for slide in presentation.slides:
                slide_text = ""
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        slide_text += shape.text + "\n\n"
                pages.append(slide_text)

            os.unlink(temp_file_path)
            return pages
        else:
            raise ValueError("지원하지 않는 파일 형식입니다.")
    except Exception as e:
        raise e
