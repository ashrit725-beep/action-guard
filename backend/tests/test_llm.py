"""The Anthropic-only guarantee: which keys are accepted, where requests go, how failures show."""
from __future__ import annotations

import asyncio
import json
import os
import threading

import anthropic
import httpx2
import pytest

from vexen import llm

NOT_ANTHROPIC = [
    ("sk-proj-" + "a1B2c3D4" * 8, "OpenAI"),
    ("sk-svcacct-" + "a1B2c3D4" * 8, "OpenAI"),
    ("sk-emergent-" + "a1B2c3D4" * 4, "Emergent"),
    ("sk-or-v1-" + "a1b2c3d4" * 8, "OpenRouter"),
    ("AIzaSy" + "A1b2C3d4" * 4, "Google"),
    ("gsk_" + "a1B2c3D4" * 6, "Groq"),
    ("xai-" + "a1B2c3D4" * 6, "xAI"),
    ("vex_sk_live_" + "a1B2c3D4" * 5, "Vexen"),
    ("sk-" + "a1B2c3D4" * 6, "OpenAI"),
    ("just-some-random-text-that-is-long-enough", ""),
]


# --------------------------------------------------------------------------- #
# What counts as an Anthropic key
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("key, provider", NOT_ANTHROPIC)
def test_a_key_from_another_provider_is_refused(key, provider, monkeypatch):
    check = llm.check_key(key)
    assert not check.ok and check.code == "not_an_anthropic_key"
    assert "not an Anthropic API key" in check.message
    if provider:
        assert provider in check.message
    assert key not in check.message

    # ...and nothing downstream will use it
    monkeypatch.setenv("ANTHROPIC_API_KEY", key)
    assert llm.available() is False
    with pytest.raises(llm.ProviderKeyError) as refused:
        llm.client(timeout=5)
    assert refused.value.code == "not_an_anthropic_key"


def test_an_anthropic_api_key_is_accepted(anthropic_key):
    check = llm.check_key(anthropic_key)
    assert check.ok and check.key == anthropic_key
    assert llm.available() is True


@pytest.mark.parametrize("key", ["sk-ant-api03-" + "x" * 90, "sk-ant-api03-" + "Ab-_" * 24])
def test_long_and_dashed_keys_are_fine(key):
    assert llm.check_key(key).ok


def test_admin_keys_and_sign_in_tokens_are_not_api_keys():
    admin = llm.check_key("sk-ant-admin01-" + "a1B2c3D4" * 8)
    sign_in = llm.check_key("sk-ant-oat01-" + "a1B2c3D4" * 8)
    assert not admin.ok and "Admin" in admin.message
    assert not sign_in.ok and "sign-in token" in sign_in.message


def test_a_cut_off_key_is_refused():
    check = llm.check_key("sk-ant-api03-short")
    assert not check.ok and "cut short" in check.message


def test_no_key_means_the_ai_is_off():
    assert llm.check_key("").code == "missing"
    assert llm.check_key(None).code == "missing"
    assert llm.available() is False
    assert llm.status()["state"] == "missing_key"
    with pytest.raises(llm.ProviderKeyError) as refused:
        llm.require_key()
    assert refused.value.code == "missing"


def test_quotes_and_spaces_pasted_from_a_dashboard_are_removed(anthropic_key):
    assert llm.check_key(f'  "{anthropic_key}"  ').key == anthropic_key
    assert llm.check_key(f"'{anthropic_key}'").key == anthropic_key


def test_the_status_never_contains_the_key(monkeypatch, anthropic_key):
    shown = json.dumps(llm.status())
    assert anthropic_key not in shown and anthropic_key[8:24] not in shown
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-proj-" + "a1B2c3D4" * 8)
    shown = json.dumps(llm.status())
    assert "a1B2c3D4" not in shown


# --------------------------------------------------------------------------- #
# Where requests go
# --------------------------------------------------------------------------- #
def _wire(client):
    """The headers and address of the request the client would really send."""
    from anthropic._models import FinalRequestOptions

    options = FinalRequestOptions.construct(method="post", url="/v1/messages", json_data={})
    request = client._build_request(options)
    return {name.lower(): value for name, value in request.headers.items()}, str(request.url)


def test_the_client_always_talks_to_anthropic(monkeypatch, anthropic_key):
    # An environment that tries to redirect traffic or swap the credential changes nothing.
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://llm-proxy.example.test")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "someone-elses-token")
    client = llm.client(timeout=5)
    assert str(client.base_url).rstrip("/") == "https://api.anthropic.com"
    assert client.api_key == anthropic_key
    assert client.auth_token is None
    headers, url = _wire(client)
    assert url == "https://api.anthropic.com/v1/messages"
    assert headers["x-api-key"] == anthropic_key and "authorization" not in headers


def test_custom_headers_in_the_environment_cannot_replace_the_credential(monkeypatch, anthropic_key):
    hostile = ("X-Api-Key: other-credential\nAuthorization: Bearer stolen\n"
               "Host: other.example.test\nanthropic-version: 1999-01-01")
    monkeypatch.setenv("ANTHROPIC_CUSTOM_HEADERS", hostile)
    headers, url = _wire(llm.client(timeout=5))
    assert url == "https://api.anthropic.com/v1/messages"
    assert headers["x-api-key"] == anthropic_key
    assert headers["host"] == "api.anthropic.com"
    assert "authorization" not in headers and headers["anthropic-version"] != "1999-01-01"
    assert os.environ["ANTHROPIC_CUSTOM_HEADERS"] == hostile  # put back for everyone else


def test_the_startup_check_is_built_the_same_safe_way(monkeypatch, fake_anthropic, anthropic_key):
    monkeypatch.setenv("ANTHROPIC_CUSTOM_HEADERS", "X-Api-Key: other-credential")
    llm.verify()
    assert fake_anthropic.custom_headers_during_build is None  # hidden while the client is built
    assert os.environ["ANTHROPIC_CUSTOM_HEADERS"] == "X-Api-Key: other-credential"  # and restored


def test_a_workspace_id_is_sent_when_one_is_configured(monkeypatch, anthropic_key):
    monkeypatch.setenv("ANTHROPIC_WORKSPACE_ID", "  wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ  ")
    headers, _ = _wire(llm.client(timeout=5))
    assert headers["anthropic-workspace-id"] == "wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ"


@pytest.mark.parametrize("value", [
    "", "not-a-workspace", "wrkspc_", "wrkspc_short", "wrkspc_01JwQvzr7rXLA5AG\nX-Evil: 1",
])
def test_a_malformed_workspace_id_is_ignored(monkeypatch, anthropic_key, value):
    monkeypatch.setenv("ANTHROPIC_WORKSPACE_ID", value)
    headers, _ = _wire(llm.client(timeout=5))
    assert "anthropic-workspace-id" not in headers and "x-evil" not in headers


def test_invisible_characters_pasted_with_a_key_are_removed(anthropic_key):
    for noise in ("﻿", "​", " ", "‎", " \t\r\n"):
        assert llm.check_key(noise + anthropic_key + noise).ok, repr(noise)
    middle = anthropic_key[:20] + "​" + anthropic_key[20:]
    assert not llm.check_key(middle).ok  # inside the key it really is a different string


# --------------------------------------------------------------------------- #
# What Anthropic says about the key
# --------------------------------------------------------------------------- #
def _api_error(kind, status):
    request = httpx2.Request("GET", "https://api.anthropic.com/v1/models/claude-opus-5-5")
    return kind("boom", response=httpx2.Response(status, request=request), body=None)


class _FakeAnthropic:
    outcome = None
    seen = None
    custom_headers_during_build = "not built"

    def __init__(self, **kwargs):
        type(self).seen = kwargs
        type(self).custom_headers_during_build = os.environ.get("ANTHROPIC_CUSTOM_HEADERS")
        self.models = self

    def retrieve(self, model_id):
        outcome = type(self).outcome
        if isinstance(outcome, BaseException):
            raise outcome
        return object()


@pytest.fixture
def fake_anthropic(monkeypatch):
    _FakeAnthropic.outcome = None
    _FakeAnthropic.seen = None
    monkeypatch.setattr(anthropic, "Anthropic", _FakeAnthropic)
    return _FakeAnthropic


def test_a_key_anthropic_accepts_is_ready(fake_anthropic, anthropic_key):
    status = llm.verify()
    assert status["state"] == "ready" and status["available"] is True
    assert fake_anthropic.seen["base_url"] == "https://api.anthropic.com"
    assert fake_anthropic.seen["api_key"] == anthropic_key


def test_a_key_anthropic_refuses_switches_the_ai_off(fake_anthropic, anthropic_key):
    fake_anthropic.outcome = _api_error(anthropic.AuthenticationError, 401)
    status = llm.verify()
    assert status["state"] == "rejected" and status["available"] is False
    with pytest.raises(llm.ProviderKeyError) as refused:
        llm.require_key()
    assert refused.value.code == "rejected"


def test_a_key_without_access_to_the_model_switches_the_ai_off(fake_anthropic, anthropic_key):
    fake_anthropic.outcome = _api_error(anthropic.NotFoundError, 404)
    status = llm.verify()
    assert status["state"] == "model_unavailable" and status["available"] is False
    assert llm.MODEL in status["detail"]


def test_a_forbidden_lookup_does_not_condemn_the_key(fake_anthropic, anthropic_key):
    fake_anthropic.outcome = _api_error(anthropic.PermissionDeniedError, 403)
    status = llm.verify()
    assert status["state"] == "unverified" and status["available"] is True


def test_an_unreachable_anthropic_says_nothing_about_the_key(fake_anthropic, anthropic_key):
    request = httpx2.Request("GET", "https://api.anthropic.com/v1/models/claude-opus-5-5")
    fake_anthropic.outcome = anthropic.APIConnectionError(request=request)
    status = llm.verify()
    assert status["state"] == "unverified" and status["available"] is True


def test_nothing_is_sent_without_a_valid_shaped_key(fake_anthropic, monkeypatch):
    llm.verify()
    assert fake_anthropic.seen is None
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-proj-" + "a1B2c3D4" * 8)
    llm.verify()
    assert fake_anthropic.seen is None


def test_a_refused_key_stays_off_until_the_key_or_the_clock_changes(monkeypatch, anthropic_key):
    assert llm.available()
    llm.mark_rejected()
    assert not llm.available()

    # a different key is not judged by the old one's verdict
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-" + "Zz9Yy8Xx7Ww6" * 4)
    assert llm.available()

    # and the same key is tried again after the cooldown
    monkeypatch.setenv("ANTHROPIC_API_KEY", anthropic_key)
    assert not llm.available()
    monkeypatch.setattr(llm, "REJECTED_COOLDOWN_SECONDS", -1)
    assert llm.available()


# --------------------------------------------------------------------------- #
# Keeping model calls from starving the rest of the site
# --------------------------------------------------------------------------- #
def test_model_calls_run_in_a_worker_thread():
    main = threading.get_ident()
    value, worker = asyncio.run(llm.run_blocking(lambda n: (n * 2, threading.get_ident()), 21))
    assert value == 42 and worker != main


def test_too_many_waiting_calls_get_a_busy_answer(monkeypatch):
    monkeypatch.setattr(llm, "MAX_WAITING_CALLS", 0)
    with pytest.raises(llm.ProviderBusy):
        asyncio.run(llm.run_blocking(lambda: 1))


# --------------------------------------------------------------------------- #
# The server's own ceiling on AI use (sign-up is open to everyone)
# --------------------------------------------------------------------------- #
def test_the_daily_ceiling_stops_runaway_use(monkeypatch):
    monkeypatch.setenv("AI_DAILY_CALL_LIMIT", "2")
    for _ in range(2):
        assert asyncio.run(llm.run_blocking(lambda: "ok")) == "ok"
    with pytest.raises(llm.ProviderBusy) as stopped:
        asyncio.run(llm.run_blocking(lambda: "ok"))
    assert "limit for today" in str(stopped.value)


def test_calls_older_than_a_day_no_longer_count(monkeypatch):
    import time

    monkeypatch.setenv("AI_DAILY_CALL_LIMIT", "3")
    llm._calls_today.extend([time.monotonic() - 90_000] * 3)  # three calls from yesterday
    assert asyncio.run(llm.run_blocking(lambda: "ok")) == "ok"
    assert len(llm._calls_today) == 1


@pytest.mark.parametrize("value, expected", [
    ("", 500), ("abc", 500), ("-3", 500), ("0", 0), ("40", 40), (" 12 ", 12),
])
def test_the_daily_ceiling_can_be_changed_or_switched_off(monkeypatch, value, expected):
    monkeypatch.setenv("AI_DAILY_CALL_LIMIT", value)
    assert llm.daily_call_limit() == expected


def test_one_person_cannot_use_all_the_ai_capacity():
    release = threading.Event()

    async def scenario():
        slow = [asyncio.create_task(llm.run_blocking(release.wait, 5, owner="alex")) for _ in range(2)]
        await asyncio.sleep(0.3)  # let both start
        with pytest.raises(llm.ProviderBusy) as busy:
            await llm.run_blocking(lambda: 1, owner="alex")
        assert "already have AI requests running" in str(busy.value)
        assert await llm.run_blocking(lambda: "fine", owner="sam") == "fine"  # someone else is unaffected
        release.set()
        await asyncio.gather(*slow)
        assert await llm.run_blocking(lambda: "again", owner="alex") == "again"  # and alex is free again
        assert not llm._in_flight

    asyncio.run(scenario())


def test_without_a_ceiling_nothing_is_counted(monkeypatch):
    monkeypatch.setenv("AI_DAILY_CALL_LIMIT", "0")
    for _ in range(5):
        asyncio.run(llm.run_blocking(lambda: None))
    assert len(llm._calls_today) == 0
