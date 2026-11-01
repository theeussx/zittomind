import json

import httpx
import pytest
import respx

from zittomind import ZittoMind
from zittomind.config import Config
from zittomind.schemas import Model, Policy


def config():
    return Config(
        models=[
            Model(
                id="local-fixture",
                provider="ollama",
                context_window=32000,
                max_output_tokens=4096,
                streaming=True,
            )
        ],
        projects={"default": Policy(privacy="strict", allowed_providers=["ollama"])},
    )


@respx.mock
async def test_local_generation_needs_no_key():
    respx.get("http://127.0.0.1:11434/api/tags").mock(
        return_value=httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "local-fixture:latest",
                        "size": 100,
                        "details": {"format": "gguf"},
                    }
                ]
            },
        )
    )
    endpoint = respx.post("http://127.0.0.1:11434/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={
                "message": {"role": "assistant", "content": "local"},
                "done": True,
                "prompt_eval_count": 3,
                "eval_count": 2,
                "done_reason": "stop",
            },
        )
    )
    result = await ZittoMind(config()).route("hi", local_only=True)
    assert result.response.text == "local"
    assert not json.loads(endpoint.calls[0].request.content)["stream"]


@respx.mock
async def test_local_ndjson_stream():
    respx.get("http://127.0.0.1:11434/api/tags").mock(
        return_value=httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "local-fixture:latest",
                        "size": 100,
                        "details": {"format": "gguf"},
                    }
                ]
            },
        )
    )
    respx.post("http://127.0.0.1:11434/api/chat").mock(
        return_value=httpx.Response(
            200,
            text='{"message":{"content":"local"},"done":false}\n{"message":{"content":""},"done":true,"prompt_eval_count":3,"eval_count":2}\n',
        )
    )
    events = [
        event async for event in ZittoMind(config()).stream("hi", local_only=True)
    ]
    assert events[0]["choices"][0]["delta"]["content"] == "local"
    assert events[-1]["usage"]["prompt_tokens"] == 3


@respx.mock
async def test_cloud_model_is_rejected_before_prompt_is_sent():
    respx.get("http://127.0.0.1:11434/api/tags").mock(
        return_value=httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "local-fixture:latest",
                        "size": 0,
                        "remote_model": "fixture",
                        "remote_host": "https://ollama.com",
                        "details": {"format": "gguf"},
                    }
                ]
            },
        )
    )
    chat = respx.post("http://127.0.0.1:11434/api/chat")
    with pytest.raises(ValueError, match="prompt was not sent"):
        await ZittoMind(config()).route("secret", local_only=True)
    assert not chat.called


def test_remote_ollama_destination_rejected():
    with pytest.raises(ValueError):
        Config(ollama_url="http://169.254.169.254/api/chat")
