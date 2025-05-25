import os
import requests
import fitz  # PyMuPDF
from pptx import Presentation
import tempfile
from io import BytesIO

def process_file_from_cloudfront(cloudfront_url):
    response = requests.get(cloudfront_url)
    file_content = response.content
    
    if cloudfront_url.endswith('.pdf'):
        pdf_document = fitz.open(stream=file_content, filetype="pdf")
        text = ""
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            text += page.get_text() + "\n"
        pdf_document.close()
        return text
        
    elif cloudfront_url.endswith('.pptx'):
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