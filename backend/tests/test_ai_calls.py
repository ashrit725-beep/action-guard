"""The two AI features, exercised with a stand-in for Anthropic's client."""
from __future__ import annotations

import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from vexen import ai, assistant, llm
from vexen.catalog import PERMISSION_CATALOG

PERMISSION = PERMISSION_CATALOG[0]["key"]
PROMPT = "Never let any agent spend more than 200 dollars without asking me first"


def _api_error(kind, status):
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return kind("boom", response=httpx2.Response(status, request=request), body=None)


def _connection_error():
    return anthropic.APIConnectionError(
        request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))


def _rule(**changes):
    rule = {
        "name": "Ask before spending",
        "description": "Anything over 200 dollars needs a person to say yes.",
        "effect": "REQUIRE_APPROVAL",
        "permissions": [PERMISSION],
        "priority": 22,
        "rationale": "Matches the request.",
        "confidence": 0.9,
    }
    rule.update(changes)
    return rule


def _reply(text, stop_reason="end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        model="claude-opus-5-5",
        content=[SimpleNamespace(type="text", text=text)],
    )


class FakeClient:
    """Stands in for anthropic.Anthropic and records what was sent."""

    def __init__(self, outcome):
        self.outcome = outcome
        self.sent = None
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.sent = kwargs
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


@pytest.fixture
def fake(monkeypatch, anthropic_key):
    def install(outcome):
        client = FakeClient(outcome)
        monkeypatch.setattr(llm, "client", lambda **_: client)
        return client

    return install


# --------------------------------------------------------------------------- #
# The rule writer
# --------------------------------------------------------------------------- #
def test_the_rule_writer_asks_claude_opus_5_5_for_a_structured_answer(fake):
    client = fake(_reply(json.dumps(_rule())))
    rule = ai.generate_policy(PROMPT)

    sent = client.sent
    assert sent["model"] == "claude-opus-5-5"
    assert sent["betas"] == ["server-side-fallback-2026-07-01"] and sent["fallbacks"] == "default"
    assert sent["output_config"]["format"]["type"] == "json_schema"
    assert sent["messages"][-1]["role"] == "user"
    for removed in ("temperature", "top_p", "top_k", "tool_choice", "thinking"):
        assert removed not in sent

    assert rule["generated_by"] == "anthropic:claude-opus-5-5"
    assert rule["effect"] == "REQUIRE_APPROVAL" and rule["match"]["permissions"] == [PERMISSION]
    assert rule["source_prompt"] == PROMPT


def test_a_refusal_is_a_failed_request_not_a_broken_generator(fake):
    fake(_reply("", stop_reason="refusal"))
    with pytest.raises(ai.PolicyGenerationError) as failed:
        ai.generate_policy(PROMPT)
    assert not isinstance(failed.value, ai.PolicyGeneratorUnavailable)
    assert "safety checks" in str(failed.value)


@pytest.mark.parametrize("raw, fragment", [
    (json.dumps(_rule(confidence=0.2)), "could not be translated"),
    (json.dumps(_rule(permissions=["not.a.real.permission"])), "Unknown permission"),
    (json.dumps(_rule(effect="MAYBE")), "Unsupported policy effect"),
    ("this is not json", "did not emit a policy"),
])
def test_an_unsafe_or_malformed_rule_is_never_returned(fake, raw, fragment):
    fake(_reply(raw))
    with pytest.raises(ai.PolicyGenerationError) as failed:
        ai.generate_policy(PROMPT)
    assert fragment in str(failed.value)


def test_a_cut_off_answer_is_not_used(fake):
    fake(_reply(json.dumps(_rule()), stop_reason="max_tokens"))
    with pytest.raises(ai.PolicyGenerationError):
        ai.generate_policy(PROMPT)


def test_a_refused_key_switches_the_rule_writer_off(fake):
    fake(_api_error(anthropic.AuthenticationError, 401))
    with pytest.raises(ai.PolicyGeneratorUnavailable) as failed:
        ai.generate_policy(PROMPT)
    assert "did not accept the AI key" in str(failed.value)
    assert ai.generator_available() is False


def test_a_key_without_model_access_switches_the_rule_writer_off(fake):
    fake(_api_error(anthropic.NotFoundError, 404))
    with pytest.raises(ai.PolicyGeneratorUnavailable):
        ai.generate_policy(PROMPT)
    assert llm.status()["state"] == "model_unavailable"


@pytest.mark.parametrize("outcome, fragment", [
    (_api_error(anthropic.RateLimitError, 429), "busy"),
    (_api_error(anthropic.InternalServerError, 500), "unavailable right now"),
    (_connection_error(), "could not reach Anthropic"),
])
def test_temporary_trouble_is_reported_plainly_and_leaves_the_key_alone(fake, outcome, fragment):
    fake(outcome)
    with pytest.raises(ai.PolicyGeneratorUnavailable) as failed:
        ai.generate_policy(PROMPT)
    assert fragment in str(failed.value)
    assert "Error" not in str(failed.value)  # no SDK class names in front of customers
    assert ai.generator_available() is True


def test_without_an_anthropic_key_the_rule_writer_says_so(monkeypatch):
    assert ai.generator_available() is False
    with pytest.raises(ai.PolicyGeneratorUnavailable) as failed:
        ai.generate_policy(PROMPT)
    assert "ANTHROPIC_API_KEY" in str(failed.value)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-proj-" + "a1B2c3D4" * 8)
    assert ai.generator_available() is False
    with pytest.raises(ai.PolicyGeneratorUnavailable) as failed:
        ai.generate_policy(PROMPT)
    assert "not an Anthropic API key" in str(failed.value)


def test_a_too_short_request_never_reaches_the_model(fake):
    client = fake(_reply(json.dumps(_rule())))
    with pytest.raises(ai.PolicyGenerationError):
        ai.generate_policy("no")
    assert client.sent is None


# --------------------------------------------------------------------------- #
# The in-app helper
# --------------------------------------------------------------------------- #
HISTORY = [{"role": "user", "content": "How do I add an agent?"}]


def test_the_helper_asks_claude_opus_5_5(fake):
    client = fake(_reply("Open My agents and press Add."))
    text, model = assistant._anthropic_reply("You are the helper.", HISTORY)
    assert (text, model) == ("Open My agents and press Add.", "anthropic:claude-opus-5-5")
    assert client.sent["model"] == "claude-opus-5-5"
    assert client.sent["system"] == "You are the helper."
    assert client.sent["fallbacks"] == "default"
    assert client.sent["messages"][-1]["role"] == "user"


def test_the_helper_reports_a_declined_or_empty_answer(fake):
    fake(_reply("", stop_reason="refusal"))
    with pytest.raises(assistant.AssistantError):
        assistant._anthropic_reply("sys", HISTORY)
    fake(_reply("   "))
    with pytest.raises(assistant.AssistantError):
        assistant._anthropic_reply("sys", HISTORY)


def test_a_refused_key_switches_the_helper_off_too(fake):
    fake(_api_error(anthropic.AuthenticationError, 401))
    with pytest.raises(assistant.AssistantError):
        assistant._anthropic_reply("sys", HISTORY)
    assert llm.available() is False


def test_the_helper_needs_an_anthropic_key():
    with pytest.raises(assistant.AssistantError) as failed:
        assistant._anthropic_reply("sys", HISTORY)
    assert "not configured" in str(failed.value)


def test_the_conversation_always_starts_and_ends_with_the_person():
    messages = [
        {"role": "assistant", "content": "Hello"},
        {"role": "user", "content": "How do I add an agent?"},
        {"role": "assistant", "content": "Open My agents."},
        {"role": "user", "content": "And then?"},
        {"role": "assistant", "content": "Press Add."},
    ]
    cleaned = assistant._clean_history(messages)
    assert cleaned[0]["role"] == "user" and cleaned[-1]["role"] == "user"
    assert [m["content"] for m in cleaned] == ["How do I add an agent?", "Open My agents.", "And then?"]
    assert assistant._clean_history([{"role": "assistant", "content": "Hi"}]) == []
    long = assistant._clean_history([{"role": "user", "content": "x" * 5000}])
    assert len(long[0]["content"]) == assistant.MAX_CHARS
