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

def test_vector_service_upsert_grant():
    from app.services.vector_db import vector_service
    from unittest.mock import MagicMock, patch
    
    # Mock index
    mock_index = MagicMock()
    
    with patch.object(vector_service, "index", mock_index), \
         patch.object(vector_service, "generate_embeddings", return_value=[0.1] * 1536) as mock_embed:
         
        metadata = {"title": "Test Grant", "funding_range": "10k-50k"}
        vector_service.upsert_grant(
            grant_id=42,
            text="This is a test grant description that should be embedded and indexed.",
            metadata=metadata
        )
        
        # Verify generate_embeddings was called
        assert mock_embed.called
        
        # Verify upsert was called
        assert mock_index.upsert.called
        
        # Check call arguments
        args, kwargs = mock_index.upsert.call_args
        assert kwargs["namespace"] == "grants"
        vectors = kwargs["vectors"]
        assert len(vectors) > 0
        assert vectors[0]["id"].startswith("grant_42_chunk_")
        assert vectors[0]["values"] == [0.1] * 1536
        assert vectors[0]["metadata"]["grant_id"] == 42
        assert vectors[0]["metadata"]["title"] == "Test Grant"
        assert "text" in vectors[0]["metadata"]

