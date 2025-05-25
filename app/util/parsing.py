import os
import requests
import fitz  # PyMuPDF
from pptx import Presentation
import tempfile
from io import BytesIO
from app.dto.request.generate_request import GenerateRequest

def process_file_from_cloudfront(generate_request: GenerateRequest):
    try:
        response = requests.get(generate_request.uploadedUrl)
        file_content = response.content
        
        if generate_request.uploadedUrl.endswith('.pdf'):
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            text = ""
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                text += page.get_text() + "\n"
            pdf_document.close()
            return text
            
        elif generate_request.uploadedUrl.endswith('.pptx'):
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            presentation = Presentation(temp_file_path)
            text = ""
            for slide in presentation.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
            
            os.unlink(temp_file_path)
            return text
        else:
            raise ValueError("지원하지 않는 파일 형식입니다.")
    except Exception as e:
        raise e
