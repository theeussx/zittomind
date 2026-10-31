"""Ollama loopback-only adapter. Never downloads models automatically."""

import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from zittomind.providers.base import post
from zittomind.schemas import Completion, Model, Request

URL = "http://127.0.0.1:11434/api/chat"


def payload(model: Model, request: Request, streaming: bool) -> dict[str, Any]:
    return {
        "model": model.id,
        "messages": [m.model_dump() for m in request.messages]
        + [{"role": "user", "content": request.prompt}],
        "stream": streaming,
        "options": {
            "num_predict": request.max_output_tokens,
            "num_ctx": model.context_window,
        },
    }


async def complete(model: Model, request: Request, timeout: float) -> Completion:
    data = await post(URL, {}, payload(model, request, False), timeout)
    try:
        if data.get("error") or not data.get("done"):
            raise ValueError("incomplete Ollama response")
        return Completion(
            text=data["message"]["content"],
            input_tokens=data["prompt_eval_count"],
            output_tokens=data["eval_count"],
            finish_reason=data.get("done_reason"),
        )
    except (KeyError, TypeError, ValueError):
        raise ValueError("invalid Ollama response") from None


async def stream(
    model: Model, request: Request, timeout: float
) -> AsyncGenerator[dict[str, Any], None]:
    ended = False
    try:
        async with httpx.AsyncClient(
            timeout=timeout, trust_env=False, follow_redirects=False
        ) as client:
            async with client.stream(
                "POST", URL, json=payload(model, request, True)
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    if data.get("error"):
                        raise ValueError("Ollama error")
                    text = data.get("message", {}).get("content", "")
                    if text:
                        yield {
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": text},
                                    "finish_reason": None,
                                }
                            ]
                        }
                    if data.get("done"):
                        yield {
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {},
                                    "finish_reason": data.get("done_reason", "stop"),
                                }
                            ]
                        }
                        yield {
                            "choices": [],
                            "usage": {
                                "prompt_tokens": data["prompt_eval_count"],
                                "completion_tokens": data["eval_count"],
                            },
                        }
                        ended = True
                        break
        if not ended:
            raise ValueError("incomplete Ollama stream")
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        raise ValueError("Ollama stream failed; partial output may exist") from None
