from __future__ import annotations

from dataclasses import dataclass
import ipaddress
from urllib.parse import ParseResult, urlparse


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
    except ValueError:
        lowered = hostname.lower()
        return lowered in {"localhost"} or lowered.endswith(".local")
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    )


def _build_candidate_url(base_url_text: str, default_scheme: str) -> str:
    raw = str(base_url_text or "").strip()
    if not raw:
        raise ValueError("base URL is empty")
    return raw if "://" in raw else f"{default_scheme}://{raw}"


def _validate_http_parts(parsed: ParseResult, allow_private_hosts: bool) -> tuple[str, str]:
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
    return scheme, hostname


def _build_normalized_url(parsed: ParseResult, scheme: str, hostname: str) -> str:
    netloc = hostname if parsed.port is None else f"{hostname}:{int(parsed.port)}"
    path = str(parsed.path or "").rstrip("/")
    return f"{scheme}://{netloc}{path}"


def _is_placeholder_host(hostname: str) -> bool:
    return hostname in _PLACEHOLDER_HOSTS or hostname.endswith(".example.com")


def parse_http_base_url(
    base_url_text: str,
    *,
    default_scheme: str = "https",
    allow_private_hosts: bool = True,
) -> HttpBaseUrl:
    parsed = urlparse(_build_candidate_url(base_url_text, default_scheme))
    scheme, hostname = _validate_http_parts(parsed, allow_private_hosts)
    return HttpBaseUrl(
        normalized=_build_normalized_url(parsed, scheme, hostname),
        hostname=hostname,
        scheme=scheme,
        port=parsed.port,
        placeholder=_is_placeholder_host(hostname) and not _is_ip_host(hostname),
    )
