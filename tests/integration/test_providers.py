import json

import httpx
import pytest
import respx

from zittomind import ZittoMind
from zittomind.config import Config
from zittomind.schemas import Model


@pytest.mark.parametrize(
    "provider,url,response",
    [
        (
            "openai",
            "https://api.openai.com/v1/chat/completions",
            {
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2},
            },
        ),
        (
            "anthropic",
            "https://api.anthropic.com/v1/messages",
            {
                "content": [{"type": "text", "text": "ok"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 2},
            },
        ),
    ],
)
@respx.mock
async def test_provider_roundtrip(provider, url, response, monkeypatch):
    monkeypatch.setenv(provider.upper() + "_API_KEY", "test-secret")
    endpoint = respx.post(url).mock(return_value=httpx.Response(200, json=response))
    model = Model(
        id="fixture", provider=provider, context_window=32000, max_output_tokens=4096
    )
    result = await ZittoMind(Config(models=[model])).route("Olá")
    assert result.response.text == "ok"
    assert result.response.input_tokens == 10
    payload = json.loads(endpoint.calls[0].request.content)
    assert payload["messages"][-1]["content"] == "Olá"
    assert "reasoning_effort" not in payload
    assert "thinking" not in payload


@respx.mock
async def test_provider_error_does_not_leak_or_retry(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    endpoint = respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(429, text="SECRET PROMPT")
    )
    model = Model(
        id="fixture", provider="openai", context_window=32000, max_output_tokens=4096
    )
    with pytest.raises(ValueError, match="HTTP 429") as error:
        await ZittoMind(Config(models=[model])).route("private")
    assert "SECRET" not in str(error.value)
    assert endpoint.call_count == 1


@respx.mock
async def test_timeout_and_malformed_response_are_sanitized(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    endpoint = respx.post("https://api.openai.com/v1/chat/completions")
    model = Model(
        id="fixture", provider="openai", context_window=32000, max_output_tokens=4096
    )
    router = ZittoMind(Config(models=[model]))
    endpoint.mock(side_effect=httpx.ReadTimeout("private details"))
    with pytest.raises(ValueError, match="transport") as error:
        await router.route("private")
    assert "private" not in str(error.value)
    endpoint.mock(return_value=httpx.Response(200, json={"choices": []}))
    with pytest.raises(ValueError, match="invalid OpenAI"):
        await router.route("private")


@respx.mock
async def test_anthropic_preserves_system_and_history(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret")
    endpoint = respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 20, "output_tokens": 1},
            },
        )
    )
    model = Model(
        id="fixture", provider="anthropic", context_window=32000, max_output_tokens=4096
    )
    router = ZittoMind(Config(models=[model]))
    await router.route(
        "Continue",
        messages=[
            {"role": "system", "content": "Instructions"},
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
        ],
    )
    payload = json.loads(endpoint.calls[0].request.content)
    assert payload["system"] == "Instructions"
    assert [m["content"] for m in payload["messages"]] == [
        "First question",
        "First answer",
        "Continue",
    ]
    with pytest.raises(ValueError, match="leading system"):
        await router.route(
            "Continue",
            messages=[
                {"role": "user", "content": "First"},
                {"role": "system", "content": "Late instructions"},
            ],
        )
