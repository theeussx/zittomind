import httpx
import pytest
import respx

from zittomind.api.app import create_app
from zittomind.config import Config
from zittomind.schemas import Model


def config():
    return Config(
        models=[
            Model(
                id="fixture",
                provider="openai",
                context_window=32000,
                max_output_tokens=4096,
                streaming=True,
            )
        ]
    )


async def test_auth_validation_and_size_limits():
    app = create_app(config(), token="test-token")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/v1/models")).status_code == 401
        headers = {"Authorization": "Bearer test-token"}
        assert (await client.get("/v1/models", headers=headers)).status_code == 200
        bad = await client.post(
            "/v1/chat/completions", headers=headers, json={"messages": "SECRET"}
        )
        assert bad.status_code == 422
        assert "SECRET" not in bad.text
        large = await client.post(
            "/v1/chat/completions", headers=headers, content=b"x" * 500001
        )
        assert large.status_code == 413


@respx.mock
async def test_real_provider_stream(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    endpoint = respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            text='data: {"choices":[{"delta":{"content":"hello"},'
            '"finish_reason":null}]}\n\n'
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}],'
            '"usage":{"prompt_tokens":2,"completion_tokens":1}}\n\n'
            "data: [DONE]\n\n",
        )
    )
    app = create_app(config(), token="test-token")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer test-token"},
            json={
                "model": "fixture",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True,
            },
        )
        assert response.status_code == 200
        assert "hello" in response.text
        assert "[DONE]" in response.text
        assert endpoint.call_count == 1


@respx.mock
async def test_partial_stream_failure_is_not_restarted(monkeypatch):
    from zittomind import ZittoMind

    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    endpoint = respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200, text='data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
        )
    )
    events = ZittoMind(config()).stream("Hi")
    assert (await anext(events))["choices"][0]["delta"]["content"] == "partial"
    with pytest.raises(ValueError, match="partial"):
        await anext(events)
    assert endpoint.call_count == 1


@respx.mock
async def test_stream_close_closes_upstream(monkeypatch):
    from zittomind import ZittoMind

    monkeypatch.setenv("OPENAI_API_KEY", "secret")

    class Body(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            yield b'data: {"choices":[{"delta":{"content":"first"}}]}\n\n'
            yield b"data: [DONE]\n\n"

        async def aclose(self):
            self.closed = True

    body = Body()
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, stream=body)
    )
    events = ZittoMind(config()).stream("Hi")
    await anext(events)
    await events.aclose()
    assert body.closed


async def test_dashboard_shell_public_metrics_private():
    app = create_app(config(), token="test-token")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        page = await client.get("/dashboard")
        assert page.status_code == 200
        assert "test-token" not in page.text
        assert (await client.get("/metrics")).status_code == 401
        result = await client.get(
            "/metrics", headers={"Authorization": "Bearer test-token"}
        )
        assert result.json()["requests"] == 0
