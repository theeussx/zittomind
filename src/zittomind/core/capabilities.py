from zittomind.core.reasoning import reasoning_parameters
from zittomind.schemas import Classification, Effort, Model, Policy, Request


def input_tokens(request: Request) -> int:
    # Conservative byte bound, not provider billing/tokenizer data.
    return (
        32
        + sum(len(m.content.encode()) + 16 for m in request.messages)
        + len(request.prompt.encode())
    )


def estimate(model: Model, request: Request) -> float | None:
    if model.input_per_million is None or model.output_per_million is None:
        return None
    return (
        input_tokens(request) * model.input_per_million
        + request.max_output_tokens * model.output_per_million
    ) / 1_000_000


def effort_for(model: Model, request: Request, task: Classification) -> Effort | None:
    return request.reasoning or (
        task.reasoning_requirement if model.reasoning_mode != "none" else None
    )


def rejection_reasons(
    model: Model, request: Request, policy: Policy, task: Classification
) -> list[str]:
    reasons = []
    if not model.enabled:
        reasons.append("disabled")
    if request.local_only or policy.privacy == "strict":
        reasons.append("privacy requires local provider (not implemented in phase 1)")
    if model.provider not in policy.allowed_providers or (
        request.provider and request.provider != model.provider
    ):
        reasons.append("provider restriction")
    if (request.model and request.model != model.id) or (
        policy.model and policy.model != model.id
    ):
        reasons.append("pinned model restriction")
    if (
        model.context_window is None
        or input_tokens(request) + request.max_output_tokens > model.context_window
    ):
        reasons.append("context limit unknown or exceeded")
    if (
        model.max_output_tokens is None
        or request.max_output_tokens > model.max_output_tokens
    ):
        reasons.append("output limit unknown or exceeded")
    for name in ("stream", "tools", "structured_output"):
        if getattr(request, name):
            reasons.append(
                "streaming unsupported" if name == "stream" else f"{name} unsupported"
            )
    ranks = {"SIMPLE": 0, "MEDIUM": 1, "ADVANCED": 2}
    if ranks[model.tier] < ranks[task.complexity]:
        reasons.append("configured capability tier insufficient")
    cost = estimate(model, request)
    if policy.max_cost_per_request is not None:
        if cost is None:
            reasons.append("price unknown under budget")
        elif cost > policy.max_cost_per_request:
            reasons.append("budget exceeded")
    try:
        reasoning_parameters(
            model, effort_for(model, request, task), request.max_output_tokens
        )
    except ValueError as exc:
        reasons.append(str(exc))
    return reasons
