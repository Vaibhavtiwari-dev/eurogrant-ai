import ipaddress

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings


def _trusted_proxy_networks() -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    return tuple(
        ipaddress.ip_network(value.strip(), strict=False)
        for value in settings.TRUSTED_PROXY_CIDRS.split(",")
        if value.strip()
    )


TRUSTED_PROXY_NETWORKS = _trusted_proxy_networks()


def _is_trusted_proxy(address: str) -> bool:
    try:
        remote_address = ipaddress.ip_address(address)
    except ValueError:
        return False
    return any(remote_address in network for network in TRUSTED_PROXY_NETWORKS)


def get_real_ip(request: Request) -> str:
    """Resolve forwarded addresses only when the direct peer is trusted."""
    remote_ip = get_remote_address(request)
    if _is_trusted_proxy(remote_ip):
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
    return remote_ip


limiter = Limiter(key_func=get_real_ip)
