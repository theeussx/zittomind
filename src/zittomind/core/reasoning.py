from typing import Any

from zittomind.schemas import Effort, Model


def reasoning_parameters(
    model: Model, effort: Effort | None, max_tokens: int
) -> dict[str, Any]:
    if effort is None:
        return {}
    if effort not in model.supported_efforts or model.reasoning_mode == "none":
        raise ValueError("unsupported reasoning effort")
    if model.reasoning_mode == "openai_effort":
        return {"reasoning_effort": effort}
    if model.reasoning_mode == "anthropic_adaptive":
        return {"thinking": {"type": "adaptive"}, "output_config": {"effort": effort}}
    budget = model.thinking_budgets.get(effort)
    if budget is None or budget >= max_tokens:
        raise ValueError("thinking budget must be configured and below output limit")
    return {"thinking": {"type": "enabled", "budget_tokens": budget}}
