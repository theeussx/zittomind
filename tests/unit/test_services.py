import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from zittomind.services.cache import Cache
from zittomind.services.resilience import CircuitBreaker
from zittomind.services.state import State


def test_atomic_budget_across_connections(tmp_path):
    path = str(tmp_path / "state.db")
    State(path).close()
    barrier = threading.Barrier(2)

    def reserve(i):
        state = State(path)
        barrier.wait()
        try:
            state.reserve(str(i), 0.7, {"project:p": 1.0})
            return True
        except ValueError:
            return False
        finally:
            state.close()

    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(reserve, range(2))) == [False, True]


def test_budget_settlement_and_retention(tmp_path):
    state = State(str(tmp_path / "state.db"))
    state.reserve("a", 0.7, {"project:p": 1})
    state.settle("a", 0.2)
    state.reserve("b", 0.7, {"project:p": 1})
    with pytest.raises(ValueError):
        state.reserve("c", 0.2, {"project:p": 1})
    state.record(
        {
            "id": "a",
            "project": "p",
            "model": "m",
            "provider": "openai",
            "cost": 0.2,
            "latency": 1.0,
            "status": "ok",
            "input_tokens": 10,
            "output_tokens": 5,
        }
    )
    assert state.stats("p")["requests"] == 1
    assert state.stats("other")["requests"] == 0
    state.close()


def test_cache_ttl_isolation_and_bound():
    now = [0.0]
    cache = Cache(2, 10, clock=lambda: now[0])
    cache.put("p", "a", {"answer": "one"})
    assert cache.get("q", "a") is None
    assert cache.get("p", "a") == {"answer": "one"}
    now[0] = 11
    assert cache.get("p", "a") is None
    for i in range(3):
        cache.put("p", str(i), i)
    assert cache.get("p", "0") is None
    assert cache.clear("p") == 2


def test_circuit_breaker_recovers_with_one_probe():
    now = [0.0]
    breaker = CircuitBreaker(2, 10, clock=lambda: now[0])
    breaker.failure("a")
    breaker.failure("a")
    assert not breaker.allow("a")
    assert breaker.allow("b")
    now[0] = 11
    assert breaker.allow("a")
    assert not breaker.allow("a")
    breaker.success("a")
    assert breaker.allow("a")


async def test_execution_records_usage_and_sanitizes_metadata():
    from zittomind.schemas import Completion, Model, Policy, Request
    from zittomind.services.execution import Execution

    state = State()
    execution = Execution(state)
    model = Model(
        id="fixture", provider="openai", input_per_million=1, output_per_million=2
    )

    async def generate():
        return Completion(text="private answer", input_tokens=10, output_tokens=5)

    result = await execution.run(
        model, Request(prompt="private prompt"), Policy(), generate
    )
    assert result.text == "private answer"
    events = state.events()
    assert events[0]["cost"] == 0.00002
    assert "private" not in str(events)


async def test_execution_keeps_reservation_on_unknown_failure():
    from zittomind.schemas import Model, Policy, Request
    from zittomind.services.execution import Execution

    state = State()
    execution = Execution(state)
    model = Model(
        id="fixture", provider="openai", input_per_million=1, output_per_million=1
    )

    async def fail():
        raise ValueError("transport failed")

    with pytest.raises(ValueError):
        await execution.run(model, Request(prompt="private"), Policy(), fail)
    assert state.stats()["errors"] == 1


async def test_response_cache_is_opt_in_and_context_sensitive():
    from zittomind.schemas import Completion, Model, Policy, Request
    from zittomind.services.execution import Execution

    execution = Execution(State())
    model = Model(id="fixture", provider="openai")
    calls = []

    async def generate():
        calls.append(1)
        return Completion(text=str(len(calls)), input_tokens=2, output_tokens=1)

    policy = Policy(response_cache=True)
    one = await execution.run(model, Request(prompt="same"), policy, generate)
    two = await execution.run(model, Request(prompt="same"), policy, generate)
    assert one.text == two.text == "1"
    three = await execution.run(
        model, Request(prompt="same", project="other"), policy, generate
    )
    assert three.text == "2"
    four = await execution.run(
        model, Request(prompt="same", no_cache=True), policy, generate
    )
    assert four.text == "3"
