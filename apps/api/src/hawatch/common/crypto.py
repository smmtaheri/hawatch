"""Small encrypted-field primitive for operator-managed secrets.

The encryption key is supplied at runtime.  Imports are intentionally lazy so
schema-only commands (for example ``migrate``) do not require decrypting data.
"""

from __future__ import annotations

import base64
import hashlib

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


ENCRYPTED_PREFIX = "v1:"


def _fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:  # pragma: no cover - exercised only in a bad image
        raise ImproperlyConfigured("cryptography is required for encrypted runtime secrets") from exc

    raw_key = str(getattr(settings, "WEATHER_PROXY_ENCRYPTION_KEY", "") or "").strip()
    if not raw_key:
        raise ImproperlyConfigured("WEATHER_PROXY_ENCRYPTION_KEY must be configured to use weather proxies")

    # Accept a normal secret from deployment tooling and derive a stable Fernet
    # key.  This avoids requiring operators to handle base64 formatting.
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


class EncryptedTextField(models.TextField):
    """TextField that transparently encrypts values before DB persistence."""

    description = "Encrypted text"

    def get_prep_value(self, value):
        if value is None:
            return None
        text = str(value)
        if not text:
            return ""
        return ENCRYPTED_PREFIX + _fernet().encrypt(text.encode("utf-8")).decode("ascii")

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        if not str(value).startswith(ENCRYPTED_PREFIX):
            raise ImproperlyConfigured("weather proxy secret is not encrypted")
        try:
            return _fernet().decrypt(str(value)[len(ENCRYPTED_PREFIX) :].encode("ascii")).decode("utf-8")
        except Exception as exc:  # cryptography exposes multiple invalid-token errors
            raise ImproperlyConfigured("weather proxy secret cannot be decrypted") from exc

    def to_python(self, value):
        return value
