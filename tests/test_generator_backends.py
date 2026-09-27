"""Groq generator: configuration and error handling, with the network call stubbed out."""
import types

import groq
import httpx
import pytest

from src import generator as g


def fake_client(content=None, error=None, seen=None):
    def create(**kwargs):
        if seen is not None:
            seen.update(kwargs)
        if error:
            raise error
        msg = types.SimpleNamespace(content=content)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])
    completions = types.SimpleNamespace(create=create)
    return lambda **_: types.SimpleNamespace(chat=types.SimpleNamespace(completions=completions))


def test_missing_key_raises_clear_error(monkeypatch):
    monkeypatch.setattr(g, "GROQ_API_KEY", "")
    with pytest.raises(g.GenerationError, match="GROQ_API_KEY"):
        g.complete("sys", "user")


def test_returns_model_text_and_sends_grounded_prompt(monkeypatch):
    seen = {}
    monkeypatch.setattr(g, "GROQ_API_KEY", "gsk_test")
    monkeypatch.setattr(g, "GROQ_MODEL", "qwen/qwen3.8-27b")
    monkeypatch.setattr(g.groq, "Groq", fake_client("The exit load is 1%.", seen=seen))
    assert g.generate("Exit load?", [{"text": "Exit load: 1%"}]) == "The exit load is 1%."
    assert seen["temperature"] == 0 and seen["reasoning_effort"] == "none"
    assert seen["messages"][0]["content"] == g.SYSTEM_PROMPT
    assert "CONTEXT:\nExit load: 1%" in seen["messages"][1]["content"]


def test_api_errors_become_generation_errors(monkeypatch):
    monkeypatch.setattr(g, "GROQ_API_KEY", "gsk_test")
    req = httpx.Request("POST", "https://api.groq.com")
    err = groq.AuthenticationError("bad key", response=httpx.Response(401, request=req), body=None)
    monkeypatch.setattr(g.groq, "Groq", fake_client(error=err))
    with pytest.raises(g.GenerationError, match="Invalid Groq API key"):
        g.complete("sys", "user")
