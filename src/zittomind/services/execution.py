"""Execution accounting shared by SDK, proxy and classifier calls."""

import asyncio
import hashlib
import json
import random
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import aclosing
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from zittomind.core.capabilities import estimate
from zittomind.providers.base import ProviderError
from zittomind.schemas import Completion, Model, Policy, Request
from zittomind.services.cache import Cache
from zittomind.services.resilience import CircuitBreaker, RateLimiter
from zittomind.services.state import State


def scope_limits(policy: Policy, request: Request, model: Model) -> dict[str, float]:
    now = datetime.now(UTC)
    values = {
        "project": request.project,
        "session": getattr(request, "session", None),
        "model": model.id,
        "provider": model.provider,
        "day": now.strftime("%Y-%m-%d"),
        "month": now.strftime("%Y-%m"),
    }
    limits = {}
    for scope, limit in getattr(policy, "budgets", {}).items():
        if not values.get(scope):
            raise ValueError("session identifier required by budget policy")
        limits[f"{request.project}:{scope}:{values[scope]}"] = limit
    if policy.max_cost_per_request is not None:
        limits[f"request:{request.operation_id}"] = policy.max_cost_per_request
    return limits


class Execution:
    def __init__(self, state: State, concurrency: int = 8, per_minute: int = 60):
        self.state = state
        self.responses = Cache()
        self.classifications = Cache()
        self.metadata = Cache()
        self.prices = Cache()
        self.breaker = CircuitBreaker()
        self.limiter = RateLimiter(per_minute)
        self.semaphore = asyncio.Semaphore(concurrency)

    async def run(
        self,
        model: Model,
        request: Request,
        policy: Policy,
        generate: Callable[[], Awaitable[Completion]],
    ) -> Completion:
        event_id = uuid4().hex
        key = hashlib.sha256(
            json.dumps(
                {
                    "request": request.model_dump(),
                    "model": model.model_dump(),
                    "policy": policy.model_dump(),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        cache_enabled = getattr(policy, "response_cache", False) and not getattr(
            request, "no_cache", False
        )
        cached = self.responses.get(request.project, key) if cache_enabled else None
        if cached is not None:
            response = Completion.model_validate(cached)
            self.state.record(
                {
                    "id": event_id,
                    "project": request.project,
                    "model": model.id,
                    "provider": model.provider,
                    "cost": 0,
                    "status": "ok",
                    "cache_hit": True,
                    "latency": 0,
                }
            )
            return response
        async with self.semaphore:
            self.limiter.check(request.project)
            if not self.breaker.allow(model.id):
                raise ValueError("provider circuit open")
            try:
                amount = estimate(model, request)
                limits = scope_limits(policy, request, model)
                if limits and amount is None:
                    raise ValueError("price unknown under aggregate budget")
                self.state.reserve(event_id, amount or 0, limits)
            except BaseException:
                self.breaker.abandon(model.id)
                raise
            started = time.monotonic()
            event: dict[str, Any] = {
                "id": event_id,
                "project": request.project,
                "model": model.id,
                "provider": model.provider,
                "estimated_cost": amount,
                "cost": None,
                "status": "error",
            }
            try:
                for attempt in range(policy.safe_retries + 1):
                    try:
                        response = await generate()
                        break
                    except ProviderError as exc:
                        if exc.status != 429 or attempt == policy.safe_retries:
                            raise
                        await asyncio.sleep(random.uniform(0.05, 0.15) * 2**attempt)
                cost = None
                if (
                    model.input_per_million is not None
                    and model.output_per_million is not None
                ):
                    cost = (
                        response.input_tokens * model.input_per_million
                        + response.output_tokens * model.output_per_million
                    ) / 1_000_000
                    self.state.settle(event_id, cost)
                self.breaker.success(model.id)
                event.update(
                    cost=cost,
                    status="ok",
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    cached_tokens=response.cached_tokens,
                    reasoning_tokens=response.reasoning_tokens,
                )
                if cache_enabled:
                    self.responses.put(request.project, key, response.model_dump())
                return response
            except BaseException:
                # Unknown outcomes retain reservations, including cancellation.
                self.breaker.failure(model.id)
                raise
            finally:
                event["latency"] = time.monotonic() - started
                self.state.record(event)

    async def stream(
        self,
        model: Model,
        request: Request,
        policy: Policy,
        generate: Callable[[], "AsyncGenerator[dict[str, Any], None]"],
    ) -> "AsyncGenerator[dict[str, Any], None]":
        event_id = uuid4().hex
        async with self.semaphore:
            self.limiter.check(request.project)
            if not self.breaker.allow(model.id):
                raise ValueError("provider circuit open")
            try:
                amount = estimate(model, request)
                limits = scope_limits(policy, request, model)
                if limits and amount is None:
                    raise ValueError("price unknown under aggregate budget")
                self.state.reserve(event_id, amount or 0, limits)
            except BaseException:
                self.breaker.abandon(model.id)
                raise
            started = time.monotonic()
            event: dict[str, Any] = {
                "id": event_id,
                "project": request.project,
                "model": model.id,
                "provider": model.provider,
                "estimated_cost": amount,
                "cost": None,
                "status": "error",
            }
            usage: dict[str, int] = {}
            try:
                async with aclosing(generate()) as events:
                    async for chunk in events:
                        if chunk.get("usage"):
                            usage.update(chunk["usage"])
                        yield chunk
                event["status"] = "ok"
                if "prompt_tokens" in usage and "completion_tokens" in usage:
                    event.update(
                        input_tokens=usage["prompt_tokens"],
                        output_tokens=usage["completion_tokens"],
                    )
                    if (
                        model.input_per_million is not None
                        and model.output_per_million is not None
                    ):
                        cost = (
                            usage["prompt_tokens"] * model.input_per_million
                            + usage["completion_tokens"] * model.output_per_million
                        ) / 1_000_000
                        self.state.settle(event_id, cost)
                        event["cost"] = cost
                self.breaker.success(model.id)
            except BaseException:
                self.breaker.failure(model.id)
                raise
            finally:
                event["latency"] = time.monotonic() - started
                self.state.record(event)
