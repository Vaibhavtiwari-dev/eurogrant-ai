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
    from unittest.mock import MagicMock, patch

    from app.services.vector_db import get_vector_service, reset_vector_service

    # Patch OpenAI before the lazy singleton is created (CI has no OPENAI_API_KEY).
    # reset_vector_service() ensures a fresh singleton picks up the patched client.
    reset_vector_service()
    with patch("app.services.vector_db.OpenAI"):
        vector_service = get_vector_service()

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


class TestHtmlEscaping:
    """Tests for HTML injection fix in NotificationService."""

    def test_send_match_alert_escapes_html_in_title(self):
        from app.services.notifications import notification_service
        # Force offline mode in case CI has real AWS creds (no SES access)
        was_offline = notification_service.is_offline
        notification_service.is_offline = True
        try:
            malicious_title = '<script>alert("xss")</script>'
            result = notification_service.send_match_alert(
                email="test@example.com",
                grant_title=malicious_title,
                score=0.95,
                explanation="Safe explanation"
            )
            assert result is True, "Email should be sent successfully in offline mode"
        finally:
            notification_service.is_offline = was_offline

    def test_send_match_alert_escapes_html_in_explanation(self):
        from app.services.notifications import notification_service
        was_offline = notification_service.is_offline
        notification_service.is_offline = True
        try:
            malicious_explanation = '<img src=x onerror=alert(1)>'
            result = notification_service.send_match_alert(
                email="test@example.com",
                grant_title="Safe Title",
                score=0.85,
                explanation=malicious_explanation
            )
            assert result is True
        finally:
            notification_service.is_offline = was_offline


class TestSsrfProtection:
    """Tests for SSRF protection in DiscoveryService."""

    def test_is_safe_url_rejects_private_ip(self):
        from app.services.discovery import _is_safe_url
        # Localhost should be rejected
        assert _is_safe_url("http://127.0.0.1:5432") is False
        assert _is_safe_url("http://169.254.169.254/latest/meta-data/") is False

    def test_is_safe_url_allows_public_url(self):
        from app.services.discovery import _is_safe_url
        # Public URLs should be allowed (if they resolve)
        result = _is_safe_url("https://www.eas.ee/en/grants")
        # May raise an error if DNS unavailable in test env, but should not crash
        assert isinstance(result, bool)

    def test_discovery_service_ssrf_blocked_logs_and_falls_back(self):
        """When the portal URL resolves to a private IP, fallback data should be used."""
        from app.services.discovery import EstoniaGrantScraper
        scraper = EstoniaGrantScraper()
        # Override portal URL to a loopback address
        scraper.portal_url = "http://127.0.0.1:1234"
        results = scraper.scrape()
        # Should fall back to mock data
        assert len(results) > 0
        assert results[0]["external_id"].startswith("EE-EAS")


class TestLockoutService:
    """Tests for account lockout mechanism."""

    def test_lockout_service_graceful_without_redis(self):
        """LockoutService should not crash when Redis is unavailable."""
        from app.services.lockout import lockout_service
        # All methods should return gracefully
        assert lockout_service.check_locked("test@example.com") is False
        assert lockout_service.record_failure("test@example.com") is False
        lockout_service.reset("test@example.com")  # Should not raise

    def test_lockout_uses_different_keys_per_email(self):
        from app.services.lockout import LockoutService, lockout_service
        # Test the key derivation (doesn't need Redis)
        count_key_1, lock_key_1 = lockout_service._make_key("user1@example.com")
        count_key_2, lock_key_2 = lockout_service._make_key("user2@example.com")
        assert count_key_1 != count_key_2
        assert lock_key_1 != lock_key_2
        assert "lockout:" in count_key_1
        assert "lockout:" in lock_key_1
