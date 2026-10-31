from typing import Any

from zittomind.providers.base import post
from zittomind.schemas import Completion, Model, Request


async def complete(
    model: Model, request: Request, params: dict[str, Any], key: str, timeout: float
) -> Completion:
    data = await post(
        "https://api.openai.com/v1/chat/completions",
        {"Authorization": f"Bearer {key}"},
        {
            "model": model.id,
            "messages": [m.model_dump() for m in request.messages]
            + [{"role": "user", "content": request.prompt}],
            model.output_parameter: request.max_output_tokens,
            **params,
        },
        timeout,
    )
    try:
        choice = data["choices"][0]
        return Completion(
            text=choice["message"]["content"],
            input_tokens=data["usage"]["prompt_tokens"],
            output_tokens=data["usage"]["completion_tokens"],
            cached_tokens=data["usage"]
            .get("prompt_tokens_details", {})
            .get("cached_tokens", 0),
            reasoning_tokens=data["usage"]
            .get("completion_tokens_details", {})
            .get("reasoning_tokens", 0),
            finish_reason=choice.get("finish_reason"),
        )
    except (KeyError, IndexError, TypeError, ValueError):
        raise ValueError("invalid OpenAI response") from None
