from types import SimpleNamespace

from app.limiter import get_real_ip


def _request(remote_ip: str, forwarded_for: str | None = None):
    headers = {}
    if forwarded_for:
        headers["X-Forwarded-For"] = forwarded_for
    return SimpleNamespace(client=SimpleNamespace(host=remote_ip), headers=headers)


def test_trusted_proxy_uses_forwarded_client_ip():
    request = _request("127.0.0.1", "203.0.113.5, 127.0.0.1")
    assert get_real_ip(request) == "203.0.113.5"


def test_untrusted_client_cannot_spoof_forwarded_ip():
    request = _request("198.51.100.5", "203.0.113.5")
    assert get_real_ip(request) == "198.51.100.5"
