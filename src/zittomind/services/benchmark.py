"""Offline classification/routing benchmark. Never generates paid responses."""

import time
from typing import Any

from zittomind.core.classifier import classify
from zittomind.schemas import Request

FIXTURES = [
    ("short_hard", "Prove P = NP", "ADVANCED"),
    ("long_simple", "Formate: " + "abc " * 5000, "SIMPLE"),
    ("code", "```python\nraise ValueError()\n```", "MEDIUM"),
    ("security", "Auditoria de segurança", "ADVANCED"),
    ("continuation", "Continue corrigindo o erro anterior", "MEDIUM"),
    ("simple", "Explique chmod", "SIMPLE"),
]


def benchmark() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for category, prompt, expected in FIXTURES:
        started = time.perf_counter()
        result = classify(Request(prompt=prompt))
        rows.append(
            {
                "category": category,
                "expected": expected,
                "predicted": result.complexity,
                "correct": result.complexity == expected,
                "overhead_ms": (time.perf_counter() - started) * 1000,
            }
        )
    return {
        "mode": "offline-fixtures",
        "cases": rows,
        "classification_accuracy": sum(r["correct"] for r in rows) / len(rows),
        "generation_quality": None,
        "provider_latency": None,
        "net_savings": None,
        "paid_calls": 0,
    }


async def compare(router: Any) -> dict[str, Any]:
    import asyncio

    from zittomind import ZittoMind

    ordered = sorted(router.config.models, key=lambda m: (m.priority, m.id))
    if not ordered:
        raise ValueError("configure models for routing benchmark")
    cases: list[tuple[str, str, dict[str, Any]]] = [
        (name, prompt, {}) for name, prompt, _ in FIXTURES
    ]
    cases += [
        (
            "context",
            "Continue",
            {"messages": [{"role": "user", "content": "Auditoria de segurança"}]},
        ),
        ("tools", "Use a tool", {"tools": True}),
        ("structured", "Return JSON", {"structured_output": True}),
        ("stream", "Hello", {"stream": True}),
    ]
    reports = []
    for strategy in [
        "fixed_economy",
        "fixed_advanced",
        "rules",
        "hybrid_local",
        "adaptive",
    ]:
        configuration = router.config.model_copy(deep=True)
        configuration.state_path = ":memory:"
        configuration.ris_enabled = strategy == "adaptive"
        configuration.adaptive_enabled = strategy == "adaptive"
        configuration.observation_only = False
        candidate = ZittoMind(configuration)
        for evaluation in router.history.evaluations():
            candidate.history.feedback(evaluation)
        active = router.history.active()
        if active:
            candidate.history.save({"weights": active["weights"]}, activate=True)

        async def run_case(
            case: tuple[str, str, dict[str, Any]],
            candidate: ZittoMind = candidate,
            strategy: str = strategy,
        ) -> dict[str, Any]:
            name, prompt, options = case
            pin = (
                ordered[0].id
                if strategy == "fixed_economy"
                else ordered[-1].id
                if strategy == "fixed_advanced"
                else None
            )
            started = time.perf_counter()
            try:
                result = await candidate.route(
                    prompt,
                    **options,
                    model=pin,
                    dry_run=True,
                    external_classification=False,
                )
                return {
                    "case": name,
                    "selected": result.decision.model_id,
                    "estimated_cost": result.decision.estimated_cost,
                    "overhead_ms": (time.perf_counter() - started) * 1000,
                    "rejected": False,
                }
            except ValueError:
                return {
                    "case": name,
                    "selected": None,
                    "estimated_cost": None,
                    "overhead_ms": (time.perf_counter() - started) * 1000,
                    "rejected": True,
                }

        try:
            results = await asyncio.gather(*(run_case(case) for case in cases))
            reports.append({"strategy": strategy, "cases": results})
        finally:
            candidate.close()
    return {
        **benchmark(),
        "strategies": reports,
        "note": (
            "Offline policy comparison. Hybrid uses local classification only; "
            "no provider generations or measured savings."
        ),
    }
