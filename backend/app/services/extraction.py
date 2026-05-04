import pdfplumber
import docx
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

class ExtractionService:
    def extract_text(self, file_content: bytes, content_type: str) -> str:
        if "pdf" in content_type:
            return self._extract_from_pdf(file_content)
        elif "wordprocessingml" in content_type or "docx" in content_type:
            return self._extract_from_docx(file_content)
        else:
            logger.warning(f"Unsupported content type for extraction: {content_type}")
            return ""

    def _extract_from_pdf(self, file_content: bytes) -> str:
        text = ""
        try:
            with pdfplumber.open(BytesIO(file_content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.error(f"Error extracting from PDF: {e}")
            raise e
        return text

    def _extract_from_docx(self, file_content: bytes) -> str:
        text = ""
        try:
            doc = docx.Document(BytesIO(file_content))
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            logger.error(f"Error extracting from DOCX: {e}")
            raise e
        return text

extraction_service = ExtractionService()
