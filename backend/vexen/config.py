"""Start-up checks: say plainly what is wrong with the setup instead of failing later.

``check()`` returns ``(problems, notes)``. A problem stops the server from
starting, because it could not work (no database address, a signing secret
anyone could guess). A note is logged and the server starts anyway (email not
set up, AI switched off).
"""
from __future__ import annotations

import os
from typing import List, Tuple

from . import llm, urls

MIN_SECRET_LENGTH = 32


def check() -> Tuple[List[str], List[str]]:
    problems: List[str] = []
    notes: List[str] = []

    mongo = (os.environ.get("MONGO_URL") or "").strip()
    if not mongo:
        problems.append(
            "MONGO_URL is not set. Add your MongoDB connection string "
            "(it starts with mongodb+srv:// or mongodb://)."
        )
    elif not mongo.startswith(("mongodb://", "mongodb+srv://")):
        problems.append("MONGO_URL is not a MongoDB connection string: it must start with mongodb+srv:// or mongodb://.")
    elif "<" in mongo or ">" in mongo:
        problems.append(
            "MONGO_URL still has a <placeholder> in it. Replace <db_password> "
            "(angle brackets included) with the database user's real password."
        )

    secret = os.environ.get("JWT_SECRET") or ""
    if len(secret) < MIN_SECRET_LENGTH:
        problems.append(
            f"JWT_SECRET must be at least {MIN_SECRET_LENGTH} characters long. "
            "Generate one with: python backend/scripts/gen_secrets.py"
        )

    if not (os.environ.get("API_KEY_PEPPER") or ""):
        notes.append(
            "API_KEY_PEPPER is empty. Set it once, before the first agent key is created, "
            "and never change it afterwards: changing it stops every agent key from working."
        )

    ai = llm.status()
    if not ai["available"]:
        notes.append("The AI features are switched off. " + ai["detail"])

    for name in llm.IGNORED_ENV:
        if (os.environ.get(name) or "").strip():
            notes.append(f"{name} is set but ignored: Vexen only uses {llm.KEY_ENV} "
                         f"and only talks to {llm.API_URL}.")
    if (os.environ.get(llm.WORKSPACE_ENV) or "").strip() and not llm.workspace_id():
        notes.append(f"{llm.WORKSPACE_ENV} is not a workspace ID (it looks like wrkspc_...), so it is ignored.")

    # Links in approval emails carry a signed token. They must come from configuration: a request's
    # own headers are chosen by whoever sends it, and an agent's call is what creates the email.
    # A production container (VEXEN_ENV=production, set in the Dockerfile) refuses to start without one.
    production = (os.environ.get("VEXEN_ENV") or "").strip().lower() == "production"
    public_setting = (os.environ.get("PUBLIC_APP_URL") or "").strip()
    configured = urls.configured_public_url()
    if public_setting and not urls.is_address(public_setting):
        message = ("PUBLIC_APP_URL must start with https:// (for example https://vexen.example.com), "
                   "so it is being ignored.")
        (problems if production and not configured else notes).append(message)
    elif not configured:
        message = ("PUBLIC_APP_URL is not set. Set it to your site's address (for example "
                   "https://vexen.example.com): approval emails link to it.")
        (problems if production else notes).append(message)
    if public_setting and urls.is_loopback(public_setting) and configured and not urls.is_loopback(configured):
        notes.append(f"PUBLIC_APP_URL points at this machine, so the host's own address "
                     f"({configured}) is used for links instead.")

    smtp = [os.environ.get(name) for name in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD")]
    if any(smtp) and not all(smtp):
        notes.append("Email is half set up: SMTP_HOST, SMTP_USERNAME and SMTP_PASSWORD are all needed.")

    vapid = [os.environ.get("VAPID_PUBLIC_KEY"), os.environ.get("VAPID_PRIVATE_KEY")]
    if any(vapid) and not all(vapid):
        notes.append("Phone notifications are half set up: VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY are both needed.")

    return problems, notes
