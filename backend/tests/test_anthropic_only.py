"""Nothing but Anthropic can be wired in: no other provider's SDK, key, client or HTTP call in the backend.

The checks read the code structurally (imports and calls), not just for words, and a second group of
tests feeds them deliberately sneaky code to prove they would catch it.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
RUNTIME = [BACKEND / "server.py", *sorted((BACKEND / "vexen").rglob("*.py"))]
DOOR = BACKEND / "vexen" / "llm.py"

OTHER_SDKS = {
    "openai", "litellm", "emergentintegrations", "google", "vertexai", "mistralai", "cohere",
    "ollama", "groq", "together", "replicate", "boto3", "botocore", "langchain",
    "langchain_openai", "huggingface_hub", "transformers",
}
# Anything that can open a connection to an address of the caller's choosing. No runtime module imports
# one today: the Anthropic SDK (inside llm.py) and the mail, push and database libraries make the only
# outbound connections. Adding one is a decision that needs a look against the Anthropic-only rule.
HTTP_CLIENTS = {
    "httpx", "httpx2", "requests", "aiohttp", "urllib3", "socket", "urllib.request", "http.client",
    "websockets", "websocket",
}
ANTHROPIC_CLIENTS = {
    "Anthropic", "AsyncAnthropic", "AnthropicBedrock", "AsyncAnthropicBedrock", "AnthropicBedrockMantle",
    "AsyncAnthropicBedrockMantle", "AnthropicVertex", "AsyncAnthropicVertex", "AnthropicFoundry",
    "AsyncAnthropicFoundry", "AnthropicAWS", "AsyncAnthropicAWS",
}
LEFTOVERS = ("openai", "gpt-4", "gpt-5", "emergent_llm", "emergentintegrations", "litellm", "gemini")


def imported_names(source: str) -> set:
    """Every dotted module name the code imports, including 'from x import y' as x and x.y."""
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def other_providers(source: str) -> list:
    return sorted(n for n in imported_names(source) if n.split(".")[0] in OTHER_SDKS)


def http_clients(source: str) -> list:
    return sorted(n for n in imported_names(source)
                  if any(n == c or n.startswith(c + ".") for c in HTTP_CLIENTS))


def anthropic_clients(source: str) -> list:
    """Anthropic client classes that are imported by name or called, in any spelling."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "anthropic":
            found += [a.name for a in node.names if a.name in ANTHROPIC_CLIENTS]
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name in ANTHROPIC_CLIENTS:
                found.append(name)
    return sorted(set(found))


# --------------------------------------------------------------------------- #
# The real code
# --------------------------------------------------------------------------- #
def test_the_only_ai_sdk_in_use_is_anthropics():
    imported = set()
    for path in RUNTIME:
        source = path.read_text(encoding="utf-8")
        assert other_providers(source) == [], path.name
        imported |= imported_names(source)
    assert "anthropic" in imported


def test_no_runtime_module_can_call_an_arbitrary_address():
    for path in RUNTIME:
        assert http_clients(path.read_text(encoding="utf-8")) == [], (
            f"{path.name} imports an HTTP client. Check it against the Anthropic-only rule first.")


def test_only_llm_py_builds_a_client():
    for path in RUNTIME:
        if path != DOOR:
            assert anthropic_clients(path.read_text(encoding="utf-8")) == [], (
                f"{path.name} must go through vexen/llm.py")
    assert anthropic_clients(DOOR.read_text(encoding="utf-8")) == ["Anthropic"]


def test_only_llm_py_reads_the_key_or_the_address():
    needles = ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_CUSTOM_HEADERS")
    for path in RUNTIME:
        if path == DOOR:
            continue
        source = path.read_text(encoding="utf-8")
        for needle in needles:
            assert needle not in source, f"{path.name} must go through vexen/llm.py (found {needle})"


def test_the_requirements_name_no_other_ai_provider():
    for name in ("requirements.txt", "requirements-dev.txt"):
        text = (BACKEND / name).read_text(encoding="utf-8").lower()
        for package in sorted(OTHER_SDKS):
            assert not re.search(rf"^\s*{re.escape(package)}\b", text, re.M), f"{name} lists {package}"


def test_no_leftovers_of_an_earlier_provider():
    for path in RUNTIME:
        if path == DOOR:  # llm.py names other providers on purpose, to explain a wrong key
            continue
        source = path.read_text(encoding="utf-8").lower()
        for word in LEFTOVERS:
            assert word not in source, f"{path.name} mentions {word}"


def test_the_model_is_set_in_one_place():
    from vexen import ai, assistant, llm

    assert llm.MODEL == "claude-opus-5-5"
    assert ai.MODEL == assistant.MODEL == llm.MODEL
    for path in RUNTIME:
        if path != DOOR:
            assert "claude-opus" not in path.read_text(encoding="utf-8"), path.name


# --------------------------------------------------------------------------- #
# The guards themselves: would they catch someone trying to get around them?
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("source", [
    "from anthropic import Anthropic\nclient = Anthropic()",
    "import anthropic\nclient = anthropic.Anthropic()",
    "import anthropic as a\nclient = a.AsyncAnthropic()",
    "from anthropic import AnthropicBedrockMantle as M\nM()",
    "from anthropic import Anthropic as Quiet",
])
def test_a_second_anthropic_client_is_caught(source):
    assert anthropic_clients(source) != []


@pytest.mark.parametrize("source", [
    "import requests\nrequests.post('https://openrouter.ai/api/v1/chat/completions')",
    "import httpx\nhttpx.post('https://example.test')",
    "import urllib.request",
    "from http.client import HTTPSConnection",
    "import aiohttp",
])
def test_a_call_to_some_other_address_is_caught(source):
    assert http_clients(source) != []


@pytest.mark.parametrize("source", [
    "import openai",
    "from openai import OpenAI",
    "import google.generativeai as genai",
    "import litellm",
])
def test_another_providers_sdk_is_caught(source):
    assert other_providers(source) != []


def test_harmless_uses_of_the_anthropic_package_are_not_flagged():
    source = "import anthropic\ntry:\n    pass\nexcept anthropic.RateLimitError:\n    pass\n"
    assert anthropic_clients(source) == [] and other_providers(source) == [] and http_clients(source) == []
