import pdfplumber
import docx
import re
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

def redact_pii(text: str) -> str:
    # Redact Emails
    text = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[REDACTED_EMAIL]', text)
    # Redact Phone numbers (more specific pattern: + followed by 7-15 digits, or standard formats)
    # Matches patterns like +1234567890, (123) 456-7890, 123-456-7890
    phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    text = re.sub(phone_pattern, '[REDACTED_PHONE]', text)
    return text

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
