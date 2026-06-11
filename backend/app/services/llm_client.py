from openai import OpenAI

from ..config import settings

_openai_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    """Return the lazily initialized OpenAI-compatible client."""
    global _openai_client
    if _openai_client is None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY environment variable is required for AI processing")
        _openai_client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            timeout=settings.PROPOSAL_LLM_TIMEOUT_SECONDS,
        )
    return _openai_client


def _reset_openai_client() -> None:
    """Reset the cached client for isolated tests."""
    global _openai_client
    _openai_client = None
