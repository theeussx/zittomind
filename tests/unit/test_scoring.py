import pytest

from zittomind.services.adaptive import Evaluation, PolicyHistory, score
from zittomind.services.state import State


def test_unknown_metrics_remain_uncertain():
    result = score("unknown", "general", [], {"quality": 0.7, "cost": 0.3}, cost=None)
    assert result["confidence"] == 0
    assert result["quality"] is None
    assert result["score"] == 0


def test_feedback_must_be_explicit_and_finite():
    with pytest.raises(ValueError):
        Evaluation(model="m", category="general", quality=1.1)
    with pytest.raises(ValueError):
        Evaluation(model="m", category="general", quality=float("nan"))
    evaluations = [
        Evaluation(model="m", category="general", quality=0.8) for _ in range(5)
    ]
    result = score("m", "general", evaluations, {"quality": 1}, cost=None)
    assert result["quality"] == 0.8
    assert result["confidence"] == 0.5
    assert result["score"] == 0.4


def test_policy_version_observation_activation_and_rollback():
    history = PolicyHistory(State())
    one = history.save({"weights": {"quality": 1}}, activate=True)
    two = history.save({"weights": {"quality": 0.5, "cost": 0.5}}, activate=False)
    assert history.active()["version"] == one
    history.activate(two)
    assert history.active()["version"] == two
    history.activate(one)
    assert history.active()["version"] == one
    with pytest.raises(ValueError):
        history.activate(999)
    assert history.active()["version"] == one


async def test_routing_uses_evidence_only_when_enabled():
    from zittomind import ZittoMind
    from zittomind.config import Config
    from zittomind.schemas import Model

    models = [
        Model(id=m, provider="openai", context_window=32000, max_output_tokens=4096)
        for m in ["a", "b"]
    ]
    router = ZittoMind(Config(models=models))
    history = PolicyHistory(router.state)
    for _ in range(10):
        history.feedback(Evaluation(model="b", category="general", quality=0.9))
    result = await router.route("hi", dry_run=True)
    assert result.decision.model_id == "b"
    assert result.decision.scores["b"]["confidence"] > 0
    assert result.decision.scores["a"]["under_evaluated"]


async def test_policy_simulation_does_not_activate():
    from zittomind import ZittoMind
    from zittomind.config import Config
    from zittomind.schemas import Model

    router = ZittoMind(
        Config(
            models=[
                Model(
                    id="m",
                    provider="openai",
                    context_window=32000,
                    max_output_tokens=4096,
                )
            ]
        )
    )
    version = router.history.save({"weights": {"quality": 1}})
    result = await router.simulate("hi", version=version)
    assert result.response is None
    assert router.history.active() is None


def test_learning_is_bounded_and_observation_only():
    history = PolicyHistory(State())
    with pytest.raises(ValueError):
        history.learn()
    for _ in range(5):
        history.feedback(Evaluation(model="m", category="general", quality=0.8))
    history.learn()
    assert history.active() is None
    assert history.versions()[0]["weights"]["quality"] == 0.6


async def test_benchmark_has_five_strategies_and_no_generations():
    from zittomind import ZittoMind
    from zittomind.config import Config
    from zittomind.schemas import Model
    from zittomind.services.benchmark import compare

    router = ZittoMind(
        Config(
            models=[
                Model(
                    id="fixture",
                    provider="openai",
                    context_window=32000,
                    max_output_tokens=4096,
                )
            ]
        )
    )
    result = await compare(router)
    assert len(result["strategies"]) == 5
    assert result["paid_calls"] == 0
    assert result["generation_quality"] is None
    assert router.state.stats()["requests"] == 0
