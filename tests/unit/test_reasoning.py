import pytest

from zittomind.core.reasoning import reasoning_parameters
from zittomind.schemas import Model


def test_reasoning_is_provider_specific():
    openai = Model(
        id="test",
        provider="openai",
        reasoning_mode="openai_effort",
        supported_efforts=["high"],
    )
    anthropic = Model(
        id="test",
        provider="anthropic",
        reasoning_mode="anthropic_budget",
        supported_efforts=["high"],
        thinking_budgets={"high": 2048},
    )
    assert reasoning_parameters(openai, "high", 4096) == {"reasoning_effort": "high"}
    assert reasoning_parameters(anthropic, "high", 4096) == {
        "thinking": {"type": "enabled", "budget_tokens": 2048}
    }
    with pytest.raises(ValueError, match="below output"):
        reasoning_parameters(anthropic, "high", 1024)
    with pytest.raises(ValueError, match="unsupported"):
        reasoning_parameters(openai, "low", 4096)
