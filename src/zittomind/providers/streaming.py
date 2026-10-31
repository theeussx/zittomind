"""Streaming text normalization. A truncated stream is an error, never retried."""

import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from zittomind.schemas import Model, Request


async def stream(
    model: Model, request: Request, params: dict[str, Any], key: str, timeout: float
) -> AsyncGenerator[dict[str, Any]]:
    messages = [m.model_dump() for m in request.messages] + [
        {"role": "user", "content": request.prompt}
    ]
    payload: dict[str, Any] = {
        "model": model.id,
        "messages": messages,
        "stream": True,
        **params,
    }
    if model.provider == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {key}"}
        payload[model.output_parameter] = request.max_output_tokens
        payload["stream_options"] = {"include_usage": True}
    else:
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
        dialogue = False
        for message in request.messages:
            if message.role == "system" and dialogue:
                raise ValueError("Anthropic requires leading system instructions")
            dialogue |= message.role != "system"
        payload["messages"] = [m for m in messages if m["role"] != "system"]
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        if system:
            payload["system"] = system
        payload["max_tokens"] = request.max_output_tokens
    ended = False
    usage: dict[str, int] = {}
    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=False, trust_env=False
        ) as client:
            async with client.stream(
                "POST", url, headers=headers, json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        ended = True
                        break
                    event = json.loads(data)
                    if model.provider == "openai":
                        if event.get("error"):
                            raise ValueError("upstream stream error")
                        if event.get("usage"):
                            usage = event["usage"]
                            yield {"usage": usage, "choices": []}
                        for choice in event.get("choices", []):
                            delta = choice.get("delta", {})
                            if delta.get("tool_calls"):
                                raise ValueError("unsupported tool stream")
                            yield {
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": delta,
                                        "finish_reason": choice.get("finish_reason"),
                                    }
                                ]
                            }
                    else:
                        kind = event.get("type")
                        if kind == "error":
                            raise ValueError("upstream stream error")
                        if kind == "message_start":
                            usage["prompt_tokens"] = event["message"]["usage"][
                                "input_tokens"
                            ]
                        elif kind == "content_block_delta":
                            delta = event["delta"]
                            if delta.get("type") == "text_delta":
                                yield {
                                    "choices": [
                                        {
                                            "index": 0,
                                            "delta": {"content": delta["text"]},
                                            "finish_reason": None,
                                        }
                                    ]
                                }
                        elif kind == "message_delta":
                            usage["completion_tokens"] = event.get("usage", {}).get(
                                "output_tokens", 0
                            )
                            reason = event["delta"].get("stop_reason")
                            yield {
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {},
                                        "finish_reason": "length"
                                        if reason == "max_tokens"
                                        else "stop",
                                    }
                                ]
                            }
                        elif kind == "message_stop":
                            yield {"usage": usage, "choices": []}
                            ended = True
                            break
        if not ended:
            raise ValueError("upstream stream ended prematurely")
    except httpx.HTTPStatusError as exc:
        raise ValueError(f"provider HTTP {exc.response.status_code}") from None
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise ValueError("provider stream failed; partial output may exist") from None
