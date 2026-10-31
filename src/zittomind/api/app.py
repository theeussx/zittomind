"""Authenticated text Chat Completions proxy with bounded input."""

import hmac
import json
import os
import time
from collections.abc import AsyncIterator
from contextlib import aclosing, asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import Field, ValidationError

from zittomind import ZittoMind
from zittomind.config import Config
from zittomind.schemas import Contract, Message


class ChatRequest(Contract):
    model: str = "auto"
    messages: list[Message] = Field(min_length=1, max_length=100)
    stream: bool = False
    max_tokens: int = Field(default=1024, ge=1, le=100000)


def create_app(
    config: Config, token: str | None = None, project: str = "default"
) -> FastAPI:
    secret = token or os.environ.get("ZITTOMIND_PROXY_TOKEN")
    if not secret or project not in config.projects:
        raise ValueError("proxy token and valid project are required")
    router = ZittoMind(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            router.close()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.router = router

    @app.middleware("http")
    async def authenticate(request: Request, call_next: Any) -> Any:
        if request.url.path == "/dashboard" and request.method == "GET":
            return await call_next(request)
        provided = request.headers.get("authorization", "")
        if not hmac.compare_digest(provided.encode(), f"Bearer {secret}".encode()):
            return JSONResponse({"error": {"message": "Unauthorized"}}, status_code=401)
        return await call_next(request)

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard() -> HTMLResponse:
        from zittomind.api.dashboard import HTML

        return HTMLResponse(
            HTML,
            headers={
                "Cache-Control": "no-store",
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/models")
    async def models() -> dict[str, Any]:
        policy = config.projects[project]
        return {
            "object": "list",
            "data": [
                {"id": m.id, "object": "model", "owned_by": m.provider}
                for m in config.models
                if m.enabled and m.provider in policy.allowed_providers
            ],
        }

    @app.get("/metrics")
    async def metrics() -> dict[str, Any]:
        return router.state.stats(project)

    @app.delete("/cache")
    async def clear_cache() -> dict[str, int]:
        return {
            "cleared": router.execution.responses.clear(project)
            + router.execution.classifications.clear(project)
        }

    @app.post("/v1/chat/completions")
    async def chat(request: Request) -> Any:
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 500000:
                raise HTTPException(413, "Payload too large")
        try:
            payload = ChatRequest.model_validate_json(body)
            if payload.messages[-1].role != "user":
                raise ValueError("last message must be user")
        except (ValidationError, ValueError):
            raise HTTPException(422, "Invalid or unsupported request") from None
        options = {
            "messages": payload.messages[:-1],
            "project": project,
            "model": None if payload.model == "auto" else payload.model,
            "max_output_tokens": payload.max_tokens,
        }
        prompt = payload.messages[-1].content
        if payload.stream:
            events = router.stream(prompt, **options)
            try:
                first = await anext(events)
            except (ValueError, StopAsyncIteration):
                await events.aclose()
                raise HTTPException(502, "Routing or upstream failure") from None

            async def output() -> AsyncIterator[str]:
                async with aclosing(events):
                    yield "data: " + json.dumps(first) + "\n\n"
                    try:
                        async for event in events:
                            yield "data: " + json.dumps(event) + "\n\n"
                    except ValueError:
                        yield 'data: {"error":{"message":"upstream stream failed"}}\n\n'
                        return
                    yield "data: [DONE]\n\n"

            return StreamingResponse(
                output(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
            )
        try:
            result = await router.route(prompt, **options)
        except ValueError:
            raise HTTPException(502, "Routing or upstream failure") from None
        assert result.response is not None
        response = result.response
        return {
            "id": result.decision.id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": result.decision.model_id,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": response.text},
                    "finish_reason": response.finish_reason,
                }
            ],
            "usage": {
                "prompt_tokens": response.input_tokens,
                "completion_tokens": response.output_tokens,
                "total_tokens": response.input_tokens + response.output_tokens,
            },
        }

    return app
