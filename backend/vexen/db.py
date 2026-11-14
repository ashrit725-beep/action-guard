"""Mongo connection, indexes and document serialization."""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .serverless import on_vercel

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def pool_settings() -> Dict[str, int]:
    """How many database connections one process keeps.

    The container is one process serving everyone. On Vercel every function instance opens its own
    pool and many instances can run at once, so each keeps a small pool and closes idle connections:
    a free MongoDB Atlas cluster accepts at most 500 connections in all.
    """
    if on_vercel():
        return {"maxPoolSize": 10, "minPoolSize": 0, "maxIdleTimeMS": 60_000}
    return {"maxPoolSize": 200, "minPoolSize": 5}


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            os.environ["MONGO_URL"].strip(),
            serverSelectionTimeoutMS=8000,
            tz_aware=True,
            **pool_settings(),
        )
    return _client


def get_db() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        _db = get_client()[os.environ.get("DB_NAME", "vexen")]
    return _db


async def close_db() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


async def ensure_indexes() -> None:
    db = get_db()
    await db.users.create_index("email", unique=True)
    await db.users.create_index("org_id")
    await db.organizations.create_index("slug", unique=True)
    await db.memberships.create_index([("org_id", 1), ("user_id", 1)], unique=True)

    await db.agents.create_index([("org_id", 1), ("created_at", -1)])
    await db.agents.create_index([("org_id", 1), ("agent_id", 1)], unique=True)
    await db.agents.create_index([("org_id", 1), ("status", 1)])
    await db.agents.create_index([("org_id", 1), ("template_id", 1)])

    await db.permissions.create_index([("org_id", 1), ("agent_id", 1)])
    await db.permissions.create_index([("org_id", 1), ("agent_id", 1), ("key", 1)], unique=True)

    await db.policies.create_index([("org_id", 1), ("priority", 1)])
    await db.policies.create_index([("org_id", 1), ("slug", 1)], unique=True)

    await db.credentials.create_index("key_hash", unique=True)
    await db.credentials.create_index([("org_id", 1), ("agent_id", 1)])

    await db.audit_events.create_index([("org_id", 1), ("created_at", -1)])
    await db.audit_events.create_index([("org_id", 1), ("audit_id", 1)], unique=True)
    await db.audit_events.create_index([("org_id", 1), ("agent_id", 1), ("created_at", -1)])
    await db.audit_events.create_index([("org_id", 1), ("decision", 1), ("created_at", -1)])
    await db.audit_events.create_index([("org_id", 1), ("permission_key", 1), ("created_at", -1)])

    await db.approvals.create_index([("org_id", 1), ("status", 1), ("created_at", -1)])
    await db.approvals.create_index([("org_id", 1), ("id", 1)], unique=True)

    await db.authorization_requests.create_index([("org_id", 1), ("created_at", -1)])
    await db.security_events.create_index([("org_id", 1), ("created_at", -1)])
    await db.sessions.create_index([("user_id", 1), ("created_at", -1)])
    await db.sessions.create_index("id", unique=True)
    await db.notifications.create_index([("org_id", 1), ("created_at", -1)])
    await db.simulator_runs.create_index([("org_id", 1), ("created_at", -1)])
    await db.contact_messages.create_index("created_at")

    # Outbound email waits in a queue so nothing on a request path talks to SMTP.
    await db.email_outbox.create_index([("status", 1), ("next_attempt_at", 1), ("created_at", 1)])
    await db.email_outbox.create_index([("org_id", 1), ("created_at", -1)])
    await db.email_outbox.create_index("id", unique=True)
    # One alert per person per event, even if the same request is retried.
    await db.email_outbox.create_index(
        "dedupe_key", unique=True,
        partialFilterExpression={"dedupe_key": {"$type": "string"}},
    )

    # Team invitations: one pending invite per address per workspace.
    await db.invites.create_index("id", unique=True)
    await db.invites.create_index([("org_id", 1), ("status", 1), ("created_at", -1)])
    await db.invites.create_index([("org_id", 1), ("email", 1)])

    # One row per browser that asked to be notified.
    await db.push_subscriptions.create_index("endpoint", unique=True)
    await db.push_subscriptions.create_index([("org_id", 1), ("user_id", 1)])


def jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items() if k != "_id"}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def clean(doc: Optional[Dict[str, Any]], *, drop: Iterable[str] = ()) -> Optional[Dict[str, Any]]:
    """Serialize a Mongo document for JSON output, always removing internals."""
    if doc is None:
        return None
    dropped = {"_id", "password_hash", "key_hash"} | set(drop)
    return {k: jsonable(v) for k, v in doc.items() if k not in dropped}


def clean_many(docs: Iterable[Dict[str, Any]], *, drop: Iterable[str] = ()) -> List[Dict[str, Any]]:
    return [clean(d, drop=drop) for d in docs]
