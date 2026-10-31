"""SQLite metadata ledger. Reservations survive crashes; no prompts are stored."""

import json
import math
import sqlite3
import time
from pathlib import Path
from typing import Any


class State:
    def __init__(self, path: str = ":memory:"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=10, isolation_level=None)
        self.db.execute("PRAGMA busy_timeout=10000")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS spending (
                id TEXT NOT NULL, scope TEXT NOT NULL, amount REAL NOT NULL,
                PRIMARY KEY(id, scope));
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY, created REAL NOT NULL,
                project TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, created REAL NOT NULL,
                data TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 0);
        """)

    def reserve(self, request_id: str, amount: float, limits: dict[str, float]) -> None:
        if not math.isfinite(amount) or amount < 0:
            raise ValueError("invalid reservation amount")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            for scope, limit in limits.items():
                spent = self.db.execute(
                    "SELECT COALESCE(SUM(amount),0) FROM spending WHERE scope=?",
                    (scope,),
                ).fetchone()[0]
                if spent + amount > limit + 1e-12:
                    raise ValueError("aggregate budget exceeded")
                self.db.execute(
                    "INSERT INTO spending VALUES (?,?,?)", (request_id, scope, amount)
                )
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def settle(self, request_id: str, amount: float) -> None:
        if not math.isfinite(amount) or amount < 0:
            raise ValueError("invalid settlement")
        self.db.execute("UPDATE spending SET amount=? WHERE id=?", (amount, request_id))

    def record(self, event: dict[str, Any]) -> None:
        allowed = {
            "id",
            "project",
            "model",
            "provider",
            "cost",
            "estimated_cost",
            "latency",
            "status",
            "input_tokens",
            "output_tokens",
            "cache_hit",
            "fallbacks",
            "category",
            "complexity",
            "policy_version",
            "shadow_model",
            "scores",
            "feedback",
            "cached_tokens",
            "reasoning_tokens",
        }
        if set(event) - allowed:
            raise ValueError("unsupported audit field")
        self.db.execute(
            "INSERT OR REPLACE INTO events VALUES (?,?,?,?)",
            (
                event["id"],
                time.time(),
                event["project"],
                json.dumps(event, allow_nan=False),
            ),
        )

    def events(self, project: str | None = None) -> list[dict[str, Any]]:
        if project is None:
            rows = self.db.execute(
                "SELECT data FROM events ORDER BY created"
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT data FROM events WHERE project=? ORDER BY created", (project,)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def stats(self, project: str | None = None) -> dict[str, Any]:
        all_events = self.events(project)
        decisions = [e for e in all_events if e.get("status") == "decision"]
        events = [e for e in all_events if e.get("status") != "decision"]
        latencies = sorted(float(e.get("latency", 0)) for e in events)
        costs: dict[str, float] = {}
        providers: dict[str, float] = {}
        for event in events:
            cost = event.get("cost") or 0
            costs[event["model"]] = costs.get(event["model"], 0) + cost
            providers[event["provider"]] = providers.get(event["provider"], 0) + cost
        return {
            "requests": len(events),
            "input_tokens": sum(e.get("input_tokens", 0) for e in events),
            "output_tokens": sum(e.get("output_tokens", 0) for e in events),
            "calculated_cost_by_model": costs,
            "calculated_cost_by_provider": providers,
            "unknown_cost_requests": sum(e.get("cost") is None for e in events),
            "latency_mean": sum(latencies) / len(latencies) if latencies else None,
            "latency_p95": latencies[max(0, math.ceil(len(latencies) * 0.95) - 1)]
            if latencies
            else None,
            "cache_hits": sum(bool(e.get("cache_hit")) for e in events),
            "fallbacks": sum(e.get("fallbacks", 0) for e in decisions),
            "errors": sum(e.get("status") != "ok" for e in events),
        }

    def purge(self, older_than_days: int) -> int:
        if older_than_days < 0:
            raise ValueError("negative retention")
        return self.db.execute(
            "DELETE FROM events WHERE created < ?",
            (time.time() - older_than_days * 86400,),
        ).rowcount

    def close(self) -> None:
        self.db.close()
