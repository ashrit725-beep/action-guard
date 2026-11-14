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


def _address(name: str) -> str:
    """A full address from a variable, or "" when it does not hold one."""
    value = (os.environ.get(name) or "").strip().rstrip("/")
    return value if is_address(value) else ""


def _domain(name: str) -> str:
    """https:// plus the bare domain a host publishes without a scheme (Vercel, Railway), or ""."""
    domain = (os.environ.get(name) or "").strip().strip("/")
    return f"https://{domain}" if domain and "://" not in domain else ""


def vercel_address() -> str:
    """The address Vercel assigned to this deployment, or "" when not on Vercel.

    In production it is VERCEL_PROJECT_PRODUCTION_URL: your shortest custom domain once you add
    one, otherwise the project's .vercel.app domain. A preview uses its own address instead, so a
    link emailed from a preview never leads to production (another database, other sign-ins).
    """
    production = (os.environ.get("VERCEL_ENV") or "").strip().lower() == "production"
    names = ("VERCEL_PROJECT_PRODUCTION_URL",) if production else ("VERCEL_BRANCH_URL", "VERCEL_URL")
    for name in names:
        address = _domain(name)
        if address:
            return address
    return ""


def configured_public_url() -> str:
    """PUBLIC_APP_URL if set, otherwise the address the host assigned.

    Vercel publishes it as VERCEL_PROJECT_PRODUCTION_URL (see vercel_address), Render as
    RENDER_EXTERNAL_URL and Railway as RAILWAY_PUBLIC_DOMAIN. A custom domain is not visible to
    Render or Railway, so set PUBLIC_APP_URL there when you add one.
    An address that points at this machine (a leftover from a local .env file) loses to a real
    one. Returns an empty string when nothing is configured.
    """
    found: List[str] = [value for value in (
        _address("PUBLIC_APP_URL"),
        vercel_address(),
        _address("RENDER_EXTERNAL_URL"),
        _domain("RAILWAY_PUBLIC_DOMAIN"),
    ) if value]
    for value in found:
        if not is_loopback(value):
            return value
    return found[0] if found else ""
