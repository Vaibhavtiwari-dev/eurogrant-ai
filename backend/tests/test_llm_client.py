from unittest.mock import MagicMock, patch

import pytest

from app.config import settings
from app.services import llm_client


@pytest.fixture(autouse=True)
def reset_client():
    llm_client._reset_openai_client()
    yield
    llm_client._reset_openai_client()


def test_missing_api_key_fails_safely():
    original = settings.OPENAI_API_KEY
    settings.OPENAI_API_KEY = None
    try:
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            llm_client.get_openai_client()
    finally:
        settings.OPENAI_API_KEY = original


def test_client_uses_configured_base_url_and_is_cached():
    original_key = settings.OPENAI_API_KEY
    original_url = settings.OPENAI_BASE_URL
    settings.OPENAI_API_KEY = "test-key"
    settings.OPENAI_BASE_URL = "https://llm.example/v1"
    client = MagicMock()
    try:
        with patch("app.services.llm_client.OpenAI", return_value=client) as constructor:
            assert llm_client.get_openai_client() is client
            assert llm_client.get_openai_client() is client
        constructor.assert_called_once_with(
            api_key="test-key",
            base_url="https://llm.example/v1",
            timeout=settings.PROPOSAL_LLM_TIMEOUT_SECONDS,
        )
    finally:
        settings.OPENAI_API_KEY = original_key
        settings.OPENAI_BASE_URL = original_url
