from __future__ import annotations

from dataclasses import dataclass
import ipaddress
from urllib.parse import urlparse


_PLACEHOLDER_HOSTS = {
    "example.com",
    "notify.example.com",
    "payments.example.com",
    "validation.local",
}


@dataclass(frozen=True)
class HttpBaseUrl:
    normalized: str
    hostname: str
    scheme: str
    port: int | None
    placeholder: bool


def _is_ip_host(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


def _is_private_or_loopback(hostname: str) -> bool:
    try:
        ip = ipaddress.ip_address(hostname)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        )
    except ValueError:
        lowered = hostname.lower()
        return lowered in {"localhost"} or lowered.endswith(".local")


def parse_http_base_url(
    base_url_text: str,
    *,
    default_scheme: str = "https",
    allow_private_hosts: bool = True,
) -> HttpBaseUrl:
    raw = str(base_url_text or "").strip()
    if not raw:
        raise ValueError("base URL is empty")
    candidate = raw if "://" in raw else f"{default_scheme}://{raw}"
    parsed = urlparse(candidate)
    scheme = str(parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise ValueError("base URL must use http/https")
    hostname = str(parsed.hostname or "").strip().lower()
    if not hostname:
        raise ValueError("base URL hostname is required")
    if parsed.port is not None and not (1 <= int(parsed.port) <= 65535):
        raise ValueError("base URL port is out of range")
    if not allow_private_hosts and _is_private_or_loopback(hostname):
        raise ValueError("private/loopback hosts are not allowed")
    netloc = hostname
    if parsed.port is not None:
        netloc = f"{netloc}:{int(parsed.port)}"
    path = str(parsed.path or "").rstrip("/")
    normalized = f"{scheme}://{netloc}{path}"
    placeholder = hostname in _PLACEHOLDER_HOSTS or hostname.endswith(".example.com")
    if not placeholder and _is_ip_host(hostname):
        placeholder = False
    return HttpBaseUrl(
        normalized=normalized,
        hostname=hostname,
        scheme=scheme,
        port=parsed.port,
        placeholder=placeholder,
    )
