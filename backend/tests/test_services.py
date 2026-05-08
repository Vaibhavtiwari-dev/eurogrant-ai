import pytest
from app.services.extraction import ExtractionService, redact_pii

def test_redact_pii():
    text = "My email is test@example.com and my name is John Doe."
    redacted = redact_pii(text)
    assert "test@example.com" not in redacted
    assert "[REDACTED_EMAIL]" in redacted

def test_extract_text_pdf_invalid():
    # Test that it logs error and raises exception for invalid PDF
    service = ExtractionService()
    with pytest.raises(Exception):
        service.extract_text(b"some invalid content", "application/pdf")

def test_extract_text_unsupported():
    service = ExtractionService()
    text = service.extract_text(b"some content", "text/plain")
    assert text == ""
