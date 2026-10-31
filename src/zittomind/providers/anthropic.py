from typing import Any

from zittomind.providers.base import post
from zittomind.schemas import Completion, Model, Request


async def complete(
    model: Model, request: Request, params: dict[str, Any], key: str, timeout: float
) -> Completion:
    # Mid-conversation system messages cannot be moved without changing semantics.
    seen_dialogue = False
    for message in request.messages:
        if message.role == "system" and seen_dialogue:
            raise ValueError("Anthropic requires leading system instructions")
        seen_dialogue |= message.role != "system"
    payload = {
        "model": model.id,
        "messages": [m.model_dump() for m in request.messages if m.role != "system"]
        + [{"role": "user", "content": request.prompt}],
        "max_tokens": request.max_output_tokens,
        **params,
    }
    system = "\n\n".join(m.content for m in request.messages if m.role == "system")
    if system:
        payload["system"] = system
    data = await post(
        "https://api.anthropic.com/v1/messages",
        {"x-api-key": key, "anthropic-version": "2023-06-01"},
        payload,
        timeout,
    )
    try:
        text = "".join(
            block["text"] for block in data["content"] if block["type"] == "text"
        )
        return Completion(
            text=text,
            input_tokens=data["usage"]["input_tokens"],
            output_tokens=data["usage"]["output_tokens"],
            finish_reason=data.get("stop_reason"),
        )
    except (KeyError, TypeError, ValueError):
        raise ValueError("invalid Anthropic response") from None
