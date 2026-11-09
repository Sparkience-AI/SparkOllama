"""Session-only credential identity helpers."""

from __future__ import annotations

import hashlib
import hmac

MINIMUM_SALT_BYTES = 16


def credential_fingerprint(api_key: str, salt: bytes) -> str:
    """Return a non-reversible, session-scoped identity for one credential."""

    if not api_key:
        raise ValueError("A non-empty API key is required.")
    if not isinstance(salt, bytes) or len(salt) < MINIMUM_SALT_BYTES:
        raise ValueError(f"Credential salt must contain at least {MINIMUM_SALT_BYTES} bytes.")
    return hmac.new(salt, api_key.encode("utf-8"), hashlib.sha256).hexdigest()
