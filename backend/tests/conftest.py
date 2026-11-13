"""Test setup: make `vexen` importable and keep every test away from real credentials."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# A well-formed Anthropic API key that is not a real key (it only has to look right).
FAKE_ANTHROPIC_KEY = "sk-ant-api03-" + "Ab1Cd2Ef3Gh4" * 4

_CLEARED = (
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "ANTHROPIC_CUSTOM_HEADERS",
    "OPENAI_API_KEY", "EMERGENT_LLM_KEY",
    "PUBLIC_APP_URL", "RENDER_EXTERNAL_URL", "RAILWAY_PUBLIC_DOMAIN",
    "SERVE_INVESTOR_DOCS", "FRONTEND_BUILD_DIR",
    "MONGO_URL", "JWT_SECRET", "API_KEY_PEPPER",
    "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "VAPID_PUBLIC_KEY", "VAPID_PRIVATE_KEY",
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """Every test starts with no credentials and no memory of an earlier verdict."""
    for name in _CLEARED:
        monkeypatch.delenv(name, raising=False)
    from vexen import llm

    llm._reset_for_tests()
    llm._limiter = None
    yield
    llm._reset_for_tests()
    llm._limiter = None


@pytest.fixture
def anthropic_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_ANTHROPIC_KEY)
    return FAKE_ANTHROPIC_KEY
