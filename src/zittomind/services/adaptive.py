"""Evidence-based scores and immutable, explicitly activated policy versions."""

import json
import math
import time
from typing import Any, Literal

from pydantic import Field

from zittomind.schemas import Contract
from zittomind.services.state import State


class Evaluation(Contract):
    project: str = Field(default="default", min_length=1, max_length=200)
    model: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    quality: float = Field(ge=0, le=1)
    source: Literal["explicit_feedback", "benchmark"] = "explicit_feedback"
    reference: str = Field(default="", max_length=200)


def score(
    model: str,
    category: str,
    evaluations: list[Evaluation],
    weights: dict[str, float],
    *,
    cost: float | None,
    project: str = "default",
    reliability: float | None = None,
    latency: float | None = None,
) -> dict[str, Any]:
    if (
        not weights
        or any(
            k not in {"quality", "cost", "reliability", "latency"}
            or not math.isfinite(v)
            or v < 0
            for k, v in weights.items()
        )
        or sum(weights.values()) <= 0
    ):
        raise ValueError("invalid score weights")
    samples = [
        e.quality
        for e in evaluations
        if e.model == model and e.category == category and e.project == project
    ]
    quality = sum(samples) / len(samples) if samples else None
    confidence = len(samples) / (len(samples) + 5)
    components = {
        "quality": (quality or 0) * confidence,
        "cost": 1 / (1 + cost * 100) if cost is not None else 0,
        "reliability": reliability or 0,
        "latency": 1 / (1 + latency) if latency is not None else 0,
    }
    value = sum(components[k] * v for k, v in weights.items()) / sum(weights.values())
    return {
        "model": model,
        "category": category,
        "quality": quality,
        "confidence": confidence,
        "samples": len(samples),
        "score": value,
        "components": components,
        "under_evaluated": len(samples) < 5,
    }


class PolicyHistory:
    def __init__(self, state: State):
        self.state = state
        state.db.execute(
            "CREATE TABLE IF NOT EXISTS evaluations "
            "(id INTEGER PRIMARY KEY, created REAL NOT NULL, data TEXT NOT NULL)"
        )

    def feedback(self, evaluation: Evaluation) -> int:
        cursor = self.state.db.execute(
            "INSERT INTO evaluations(created,data) VALUES (?,?)",
            (time.time(), evaluation.model_dump_json()),
        )
        assert cursor.lastrowid is not None
        return cursor.lastrowid

    def evaluations(self) -> list[Evaluation]:
        return [
            Evaluation.model_validate_json(row[0])
            for row in self.state.db.execute("SELECT data FROM evaluations ORDER BY id")
        ]

    def save(self, data: dict[str, Any], *, activate: bool = False) -> int:
        # Validate the scoring policy before preserving it.
        score("", "", [], data.get("weights", {}), cost=None)
        if set(data) - {"weights"}:
            raise ValueError("unsupported adaptive policy field")
        cursor = self.state.db.execute(
            "INSERT INTO versions(created,data) VALUES (?,?)",
            (time.time(), json.dumps(data, allow_nan=False)),
        )
        assert cursor.lastrowid is not None
        version = cursor.lastrowid
        if activate:
            self.activate(version)
        return version

    def activate(self, version: int) -> None:
        self.state.db.execute("BEGIN IMMEDIATE")
        try:
            if not self.state.db.execute(
                "SELECT 1 FROM versions WHERE id=?", (version,)
            ).fetchone():
                raise ValueError("unknown policy version")
            self.state.db.execute("UPDATE versions SET active=0")
            self.state.db.execute("UPDATE versions SET active=1 WHERE id=?", (version,))
            self.state.db.execute("COMMIT")
        except BaseException:
            self.state.db.execute("ROLLBACK")
            raise

    def active(self) -> dict[str, Any] | None:
        row = self.state.db.execute(
            "SELECT id,data FROM versions WHERE active=1"
        ).fetchone()
        return {"version": row[0], **json.loads(row[1])} if row else None

    def versions(self) -> list[dict[str, Any]]:
        return [
            {
                "version": row[0],
                "created": row[1],
                "active": bool(row[3]),
                **json.loads(row[2]),
            }
            for row in self.state.db.execute(
                "SELECT id,created,data,active FROM versions ORDER BY id"
            )
        ]

    def learn(self, *, project: str = "default") -> int:
        """Propose a bounded quality-weight update; never activate automatically."""
        evidence = [e for e in self.evaluations() if e.project == project]
        if len(evidence) < 5:
            raise ValueError("at least five explicit evaluations are required")
        active = self.active()
        weights = (
            dict(active["weights"])
            if active
            else {"quality": 0.5, "cost": 0.2, "reliability": 0.2, "latency": 0.1}
        )
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}
        # Increase evidence weight by at most 0.1, without autonomous activation.
        previous = weights.get("quality", 0)
        updated = min(0.9, previous + 0.1)
        if previous < 1:
            weights = {
                k: v * (1 - updated) / (1 - previous)
                for k, v in weights.items()
                if k != "quality"
            }
            weights["quality"] = updated
        return self.save({"weights": weights})
