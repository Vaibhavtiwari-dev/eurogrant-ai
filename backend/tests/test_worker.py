import pytest
from unittest.mock import MagicMock, patch
from app.worker import process_company_document, extract_company_profile
from app import models

def test_process_company_document_success(db_session, mock_s3):
    # Setup test data
    org = models.Organization(name="Worker Org")
    db_session.add(org)
    db_session.commit()
    
    doc = models.CompanyDocument(
        organization_id=org.id,
        file_name="test.pdf",
        s3_key="key",
        content_type="application/pdf",
        status=models.DocumentStatus.PENDING
    )
    db_session.add(doc)
    db_session.commit()
    
    # Mock services
    with patch("app.worker.s3_service.get_fileobj", return_value=b"fake content"):
        with patch("app.worker.extraction_service.extract_text", return_value="Extracted text"), \
             patch("app.worker.redact_pii", return_value="Safe text"), \
             patch("app.worker.vector_service.upsert_text") as mock_vector, \
             patch("app.worker.extract_company_profile") as mock_extract:
            
            # Use a separate session for the worker but shared DB (via StaticPool in engine)
            # We don't patch SessionLocal to return db_session, we let it create its own.
            # But we need to make sure app.worker.SessionLocal uses our test engine.
            from tests.conftest import TestingSessionLocal
            with patch("app.worker.SessionLocal", TestingSessionLocal):
                process_company_document(doc.id)
                
                # Re-fetch doc using the test's db_session
                db_session.expire_all()
                updated_doc = db_session.query(models.CompanyDocument).filter(models.CompanyDocument.id == doc.id).first()
                assert updated_doc.status == models.DocumentStatus.PROCESSED
                assert mock_vector.called
                assert mock_extract.called

def test_extract_company_profile(db_session):
    org = models.Organization(name="Profile Org")
    db_session.add(org)
    db_session.commit()
    
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"sector": "Tech", "headcount_range": "11-50", "revenue_tier": "1M-5M", "legal_entity_type": "GmbH", "countries_of_operation": ["Germany"], "core_technologies": ["Python"]}'
    
    with patch("app.worker.openai_client.chat.completions.create", return_value=mock_response):
        extract_company_profile("Document text", org.id, db_session)
        
        db_session.expire_all()
        updated_org = db_session.query(models.Organization).filter(models.Organization.id == org.id).first()
        assert updated_org.sector == "Tech"
        assert updated_org.headcount_range == "11-50"
        assert updated_org.revenue_tier == "1M-5M"
        assert updated_org.legal_entity_type == "GmbH"
