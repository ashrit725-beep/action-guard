"""The site's own public address, when the operator or the host has told us.

Links in approval emails, invitations, push notifications and the developer page
all need the address people outside the server can open. That address must come
from configuration, never from request headers: a header is chosen by whoever
sends the request, and an agent's own call is what creates an approval email.
"""
from __future__ import annotations

import os
from typing import List
from urllib.parse import urlparse


def is_address(value: str) -> bool:
    """True for something that starts like a web address (https:// or http://)."""
    return value.startswith(("https://", "http://"))


def is_loopback(address: str) -> bool:
    """True when the address points at this machine (localhost, 127.x, ::1, 0.0.0.0)."""
    host = (urlparse(address).hostname or "").lower()
    return host in {"localhost", "0.0.0.0", "::1"} or host.endswith(".localhost") or host.startswith("127.")


def configured_public_url() -> str:
    """PUBLIC_APP_URL if set, otherwise the address the host assigned.

    Render publishes it as RENDER_EXTERNAL_URL and Railway as RAILWAY_PUBLIC_DOMAIN.
    A custom domain is not visible to either, so set PUBLIC_APP_URL when you add one.
    An address that points at this machine (a leftover from a local .env file) loses to a real
    one. Returns an empty string when nothing is configured.
    """
    found: List[str] = []
    for name in ("PUBLIC_APP_URL", "RENDER_EXTERNAL_URL"):
        value = (os.environ.get(name) or "").strip().rstrip("/")
        if is_address(value):
            found.append(value)
    domain = (os.environ.get("RAILWAY_PUBLIC_DOMAIN") or "").strip().strip("/")
    if domain and "://" not in domain:
        found.append(f"https://{domain}")
    for value in found:
        if not is_loopback(value):
            return value
    return found[0] if found else ""
