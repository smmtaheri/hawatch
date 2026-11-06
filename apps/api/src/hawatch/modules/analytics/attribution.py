"""Bounded, first-party attribution. Never fetch or persist an arbitrary URL."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

SOURCES = {
    "google": "گوگل",
    "bing": "بینگ",
    "instagram": "اینستاگرام",
    "telegram": "تلگرام",
    "referral": "سایت دیگر",
    "direct_unknown": "مستقیم / نامشخص",
    "unknown": "اطلاعات موجود نیست",
}
NAVIGATIONS = {
    "entry": "ورود",
    "site_search": "جست‌وجوی داخلی",
    "home": "هوم",
    "destinations": "فهرست مقصدها",
    "routes": "فهرست مسیرها",
    "point": "صفحهٔ نقطه",
    "route": "صفحهٔ مسیر",
    "history": "برگشت / جلو",
    "internal": "لینک داخلی",
    "unknown": "نامشخص",
}
PUBLIC_PATH = re.compile(
    r"^/(?:|destinations(?:/page/[1-9][0-9]*)?|routes(?:/page/[1-9][0-9]*|/[a-z0-9-]+)?|points/[a-z0-9-]+|account/plans)/?$"
)
TOKEN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
LABEL = re.compile(r"^[\w .:/-]{1,100}$", re.UNICODE)


def public_path(value):
    if (
        not isinstance(value, str)
        or len(value) > 200
        or not PUBLIC_PATH.fullmatch(value)
    ):
        return ""
    return value.rstrip("/") or "/"


def campaign_label(value):
    if not isinstance(value, str):
        return ""
    value = value.strip()
    # Campaign labels are identifiers, never free-form search/contact data.
    if (
        not LABEL.fullmatch(value)
        or "@" in value
        or re.search(r"(?:token|password|email|phone)", value, re.I)
    ):
        return ""
    digits = value.translate(
        str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    )
    if re.search(r"(?:^|\D)(?:0|98|0098)9\d{9}(?:$|\D)", digits):
        return ""
    return value


def referral_host(value):
    if not isinstance(value, str) or len(value) > 512:
        return ""
    try:
        url = urlsplit(value)
        if url.scheme not in {"http", "https"} or url.username or url.password:
            return ""
        host = (url.hostname or "").lower().rstrip(".")
        return host if re.fullmatch(r"[a-z0-9.-]{1,200}", host) else ""
    except ValueError:
        return ""


def attribution(payload):
    """Derive source on the server; preserve the evidence type alongside it."""
    host = referral_host(payload.get("referrer"))
    tag = campaign_label(payload.get("utm_source")).lower()
    aliases = {
        "google": "google",
        "bing": "bing",
        "instagram": "instagram",
        "ig": "instagram",
        "telegram": "telegram",
        "tg": "telegram",
    }
    source = aliases.get(tag, "referral") if tag else "direct_unknown"
    evidence = "utm" if tag else "none"
    if not tag and host and host not in {"hawatch.ir", "www.hawatch.ir"}:
        source = (
            "google"
            if re.search(
                r"(?:^|\.)google\.(?:com|[a-z]{2}|co\.[a-z]{2}|com\.[a-z]{2})$", host
            )
            else "referral"
        )
        for domains, key in [
            (("google.com", "google.co.uk", "google.de", "google.fr"), "google"),
            (("bing.com",), "bing"),
            (("instagram.com",), "instagram"),
            (("t.me", "telegram.org", "telegram.me"), "telegram"),
        ]:
            if any(host == d or host.endswith("." + d) for d in domains):
                source = key
                break
        evidence = "referrer"
    return {
        "source": source,
        "source_evidence": evidence,
        "utm_source": tag,
        "medium": campaign_label(payload.get("utm_medium")).lower(),
        "campaign": campaign_label(payload.get("utm_campaign")),
        "referrer_host": host,
        "landing_path": public_path(payload.get("landing_path")),
    }
