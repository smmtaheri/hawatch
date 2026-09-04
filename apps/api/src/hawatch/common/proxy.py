"""Validation and safe presentation helpers for outbound SOCKS proxies."""

from __future__ import annotations

from urllib.parse import urlsplit


SUPPORTED_PROXY_SCHEMES = {"socks5", "socks5h"}


def validate_proxy_uri(value: str) -> str:
    """Return a trimmed proxy URI or raise ``ValueError`` with a safe message."""

    text = str(value or "").strip()
    try:
        parsed = urlsplit(text)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("proxy URL is malformed") from exc
    if parsed.scheme.lower() not in SUPPORTED_PROXY_SCHEMES:
        raise ValueError("proxy URL must use socks5 or socks5h")
    if not host or port is None:
        raise ValueError("proxy URL must include a host and port")
    if not parsed.username or parsed.password is None:
        raise ValueError("proxy URL must include username and password")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("proxy URL must not include path, query or fragment")
    return text


def request_proxy_uri(value: str) -> str:
    """Prefer remote DNS resolution to avoid leaking Open-Meteo host lookups."""

    text = validate_proxy_uri(value)
    parsed = urlsplit(text)
    if parsed.scheme.lower() == "socks5":
        return "socks5h://" + text.split("://", 1)[1]
    return text


def masked_proxy_uri(value: str) -> str:
    """Show only non-secret endpoint details in Admin/log-facing surfaces."""

    try:
        parsed = urlsplit(value)
        host = parsed.hostname or "?"
        port = f":{parsed.port}" if parsed.port is not None else ""
        return f"{parsed.scheme}://***@{host}{port}"
    except ValueError:
        return "(invalid proxy)"
