"""The contact form reaches the people who run the site."""
from __future__ import annotations

import asyncio

import pytest
from starlette.requests import Request

from vexen import deps, mailer, models, routes_ops


class _Collection:
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        self.docs.append(doc)


class _Db:
    def __init__(self):
        self.contact_messages = _Collection()
        self.email_outbox = _Collection()


def _request(ip="203.0.113.7"):
    scope = {"type": "http", "method": "POST", "path": "/api/public/contact", "query_string": b"",
             "headers": [(b"user-agent", b"pytest")], "client": (ip, 1234)}
    return Request(scope)


def _payload(**changes):
    data = {"name": "Alex Morgan", "email": "alex@example.com", "company": "Acme", "topic": "sales",
            "message": "We would like to try Vexen with our agents."}
    data.update(changes)
    return models.ContactMessageIn(**data)


@pytest.fixture
def db(monkeypatch):
    fake = _Db()
    monkeypatch.setattr(routes_ops, "get_db", lambda: fake)
    deps._BUCKETS.clear()
    yield fake
    deps._BUCKETS.clear()


def test_a_message_is_saved_and_nobody_is_emailed_unless_asked(db):
    result = asyncio.run(routes_ops.submit_contact(_payload(), _request()))
    assert result["ok"] and result["reference"].startswith("VEX-MSG-")
    assert len(db.contact_messages.docs) == 1
    assert db.email_outbox.docs == []


def test_the_site_owner_gets_an_email_when_an_address_is_set(db, monkeypatch):
    monkeypatch.setenv("CONTACT_NOTIFY_EMAIL", "owner@example.com")
    result = asyncio.run(routes_ops.submit_contact(_payload(), _request("203.0.113.8")))
    (row,) = db.email_outbox.docs
    assert row["to"] == "owner@example.com" and row["kind"] == "contact_message"
    assert row["dedupe_key"] == "contact:" + result["reference"]
    assert "alex@example.com" in row["text"] and "We would like to try Vexen" in row["text"]
    assert len(db.contact_messages.docs) == 1  # saved as well


def test_what_a_visitor_types_cannot_inject_html_or_headers():
    subject, text, html = mailer.contact_message_email(
        reference="VEX-MSG-1", name="Eve\r\nBcc: spy@example.com", email="eve@example.com",
        company="<b>Evil</b>", topic="general\nX-Injected: 1", message="<script>alert(1)</script>\nline two")
    assert "\n" not in subject and "\r" not in subject
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "<b>Evil</b>" not in html
    assert "line two" in html and "<br>" in html
