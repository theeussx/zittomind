import json

import httpx
import pytest
import respx

from zittomind import ZittoMind
from zittomind.config import Config
from zittomind.schemas import Model, Policy


def configuration(**overrides):
    model = Model(
        id="fixture",
        provider="openai",
        context_window=32000,
        max_output_tokens=4096,
        input_per_million=1,
        output_per_million=1,
    )
    policy = Policy(
        external_classification=True,
        classifier_model="fixture",
        classifier_max_cost=0.01,
        **overrides,
    )
    return Config(models=[model], projects={"default": policy})


@respx.mock
async def test_dry_run_with_policy_consent_still_needs_request_consent():
    result = await ZittoMind(configuration()).route("private", dry_run=True)
    assert result.response is None
    assert not respx.calls


@respx.mock
async def test_external_requires_privacy_and_budget():
    for config in [
        configuration(privacy="strict"),
        configuration(max_cost_per_request=0),
    ]:
        with pytest.raises(ValueError):
            await ZittoMind(config).route(
                "private", dry_run=True, external_classification=True
            )
    assert not respx.calls


@respx.mock
async def test_external_sends_only_features_and_validates_json(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    output = {
        "complexity": "MEDIUM",
        "confidence": 0.8,
        "category": "general",
        "reasoning_requirement": "medium",
    }
    endpoint = respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(output)}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 30},
            },
        )
    )
    result = await ZittoMind(configuration()).route(
        "PRIVATE-123", dry_run=True, external_classification=True
    )
    assert result.decision.classification.complexity == "MEDIUM"
    assert result.decision.classifier_estimated_cost > 0
    assert "PRIVATE-123" not in endpoint.calls[0].request.content.decode()
    endpoint.mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "{bad json"}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 30},
            },
        )
    )
    with pytest.raises(ValueError, match="invalid external"):
        await ZittoMind(configuration()).route(
            "PRIVATE-123", dry_run=True, external_classification=True
        )
