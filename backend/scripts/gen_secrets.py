#!/usr/bin/env python3
"""Print fresh secrets for a Vexen deployment. It only prints; it writes nothing.

    python backend/scripts/gen_secrets.py

JWT_SECRET and API_KEY_PEPPER are random strings. CRON_SECRET protects Vercel's
scheduled email run (letters and digits only, as Vercel asks). The VAPID pair is
what lets the server send phone notifications (optional). ANTHROPIC_API_KEY is not
generated here: create it in the Anthropic Console (console.anthropic.com).
"""
from __future__ import annotations

import base64
import secrets
from typing import Tuple


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def vapid_pair() -> Tuple[str, str]:
    """(public, private) in the form browsers and pywebpush expect."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    key = ec.generate_private_key(ec.SECP256R1())
    private = key.private_numbers().private_value.to_bytes(32, "big")
    public = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return _b64url(public), _b64url(private)


def main() -> None:
    print("# Paste these into your host's environment settings. Never commit them.")
    print("# Set JWT_SECRET and API_KEY_PEPPER once: changing JWT_SECRET signs everyone out,")
    print("# and changing API_KEY_PEPPER stops every agent key from working.")
    print(f"JWT_SECRET={secrets.token_urlsafe(48)}")
    print(f"API_KEY_PEPPER={secrets.token_urlsafe(32)}")
    print("\n# Vercel only: lets Vercel's scheduled job send the queued email (see docs/DEPLOY.md)")
    print(f"CRON_SECRET={secrets.token_hex(24)}")
    try:
        public, private = vapid_pair()
    except ImportError:
        print("\n# Install backend/requirements.txt to also generate phone-notification keys.")
        return
    print("\n# Optional: phone notifications (browser push)")
    print(f"VAPID_PUBLIC_KEY={public}")
    print(f"VAPID_PRIVATE_KEY={private}")
    print("VAPID_SUBJECT=mailto:you@example.com")


if __name__ == "__main__":
    main()
