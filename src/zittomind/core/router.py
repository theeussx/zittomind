"""Public asynchronous SDK. Decisions never include prompt text."""

import hashlib
import logging
import time
from collections import OrderedDict
from collections.abc import AsyncGenerator
from contextlib import aclosing
from typing import Any

from zittomind.config import Config, Credentials, load_config
from zittomind.core.capabilities import (
    effort_for,
    estimate,
    input_tokens,
    rejection_reasons,
)
from zittomind.core.classifier import classify
from zittomind.core.reasoning import reasoning_parameters
from zittomind.core.registry import Registry
from zittomind.providers import anthropic, ollama, openai
from zittomind.schemas import (
    Classification,
    Completion,
    Decision,
    Model,
    Policy,
    Request,
    RouteResult,
)
from zittomind.services.adaptive import PolicyHistory, score
from zittomind.services.execution import Execution
from zittomind.services.state import State

logger = logging.getLogger("zittomind")


class ZittoMind:
    def __init__(self, config: Config | None = None):
        self.config = (config or load_config()).model_copy(deep=True)
        self.registry = Registry(self.config.models)
        self.state = State(self.config.state_path)
        self.execution = Execution(
            self.state, self.config.concurrency, self.config.requests_per_minute
        )
        for cache in (
            self.execution.responses,
            self.execution.classifications,
            self.execution.metadata,
            self.execution.prices,
        ):
            cache.ttl = self.config.cache_ttl
            cache.capacity = self.config.cache_capacity
        self.state.purge(self.config.retention_days)
        self.history = PolicyHistory(self.state)
        self.sessions: OrderedDict[tuple[str, str], str] = OrderedDict()

    def close(self) -> None:
        self.state.close()

    async def _complete(
        self,
        model: Model,
        request: Request,
        task: Classification,
        policy: Policy | None = None,
    ) -> Completion:
        return await self.execution.run(
            model,
            request,
            policy or self.config.projects[request.project],
            lambda: self._raw_complete(model, request, task),
        )

    async def _raw_complete(
        self, model: Model, request: Request, task: Classification
    ) -> Completion:
        if model.provider == "ollama":
            return await ollama.complete(model, request, self.config.timeout_seconds)
        credentials = Credentials()
        secret = (
            credentials.openai_api_key
            if model.provider == "openai"
            else credentials.anthropic_api_key
        )
        if secret is None or not secret.get_secret_value():
            raise ValueError(f"missing {model.provider.upper()}_API_KEY")
        complete = openai.complete if model.provider == "openai" else anthropic.complete
        params = reasoning_parameters(
            model, effort_for(model, request, task), request.max_output_tokens
        )
        return await complete(
            model,
            request,
            params,
            secret.get_secret_value(),
            self.config.timeout_seconds,
        )

    async def _external(
        self, request: Request, policy: Policy, local: Classification
    ) -> tuple[Classification, float]:
        if (
            request.local_only
            or policy.privacy == "strict"
            or not policy.external_classification
        ):
            raise ValueError("external classification forbidden by privacy/policy")
        if not policy.classifier_model:
            raise ValueError("classifier_model must be configured")
        model = self.registry.get(policy.classifier_model)
        # Send derived features only: never original text or conversation.
        probe = Request(
            prompt="Return only a Classification JSON matching this schema: "
            + Classification.model_json_schema().__str__()
            + "\nDerived local features: "
            + local.model_dump_json(),
            model=model.id,
            project=request.project,
            session=request.session,
            operation_id=request.operation_id,
            max_output_tokens=512,
        )
        task = classify(probe)
        cap = policy.classifier_max_cost
        if policy.max_cost_per_request is not None:
            cap = min(cap, policy.max_cost_per_request)
        classifier_policy = policy.model_copy(
            update={"model": model.id, "max_cost_per_request": cap}
        )
        reasons = rejection_reasons(model, probe, classifier_policy, task)
        if reasons:
            raise ValueError("classifier ineligible: " + "; ".join(reasons))
        response = await self._complete(model, probe, task, classifier_policy)
        try:
            result = Classification.model_validate_json(response.text)
        except ValueError:
            raise ValueError("invalid external classification JSON") from None
        # Remote output cannot lower local safety requirements.
        ranks = {"SIMPLE": 0, "MEDIUM": 1, "ADVANCED": 2}
        if ranks[result.complexity] < ranks[local.complexity]:
            result = local
        return result, estimate(model, probe) or 0

    async def route(self, prompt: str, **options: Any) -> RouteResult:
        request = Request(prompt=prompt, **options)
        if (
            sum(len(m.content.encode()) for m in request.messages)
            + len(prompt.encode())
            > 400000
        ):
            raise ValueError("request payload too large")
        if request.project not in self.config.projects:
            raise ValueError("unknown project")
        policy = self.config.projects[request.project].model_copy(deep=True)
        profile = request.profile or policy.profile
        if request.session and not request.model:
            request.model = self.sessions.get((request.project, request.session))
        cache_key = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
        cached_task = (
            None
            if request.no_cache
            else self.execution.classifications.get(request.project, cache_key)
        )
        task = (
            Classification.model_validate(cached_task)
            if cached_task
            else classify(request)
        )
        if not request.no_cache:
            self.execution.classifications.put(
                request.project, cache_key, task.model_dump()
            )
        if not request.model and task.category in policy.category_models:
            request.model = policy.category_models[task.category]
        classifier_cost = 0.0
        if request.external_classification and task.confidence < 0.75:
            task, classifier_cost = await self._external(request, policy, task)
            if policy.max_cost_per_request is not None:
                policy.max_cost_per_request = max(
                    0, policy.max_cost_per_request - classifier_cost
                )
        selection_request = request
        if request.shadow:
            if not request.model:
                raise ValueError("shadow requires a pinned original model")
            selection_request = request.model_copy(update={"model": None})
        rejected: dict[str, list[str]] = {}
        eligible = []
        for model in self.registry.models.values():
            reasons = rejection_reasons(model, selection_request, policy, task)
            if reasons:
                rejected[model.id] = reasons
            else:
                eligible.append(model)
        if not eligible:
            reasons = sorted({r for values in rejected.values() for r in values})
            raise ValueError(
                "no eligible model: "
                + ("; ".join(reasons) or "configure model registry")
            )

        profiles = {
            "economy": {
                "quality": 0.3,
                "cost": 0.5,
                "reliability": 0.1,
                "latency": 0.1,
            },
            "balanced": {
                "quality": 0.5,
                "cost": 0.2,
                "reliability": 0.2,
                "latency": 0.1,
            },
            "performance": {
                "quality": 0.75,
                "cost": 0.05,
                "reliability": 0.15,
                "latency": 0.05,
            },
            **self.config.profiles,
        }
        if profile not in profiles:
            raise ValueError("unknown profile")
        weights = profiles[profile]
        active = self.history.active()
        policy_version = "rules-v1"
        if active and self.config.adaptive_enabled and not self.config.observation_only:
            weights = active["weights"]
            policy_version = str(active["version"])
        evaluations = self.history.evaluations()
        scores: dict[str, dict[str, Any]] = {}
        events = self.state.events(request.project)
        for model in eligible:
            measured = [
                e
                for e in events
                if e["model"] == model.id and e.get("status") != "decision"
            ]
            reliability = (
                sum(e.get("status") == "ok" for e in measured) / len(measured)
                if measured
                else None
            )
            latency = (
                sum(e.get("latency", 0) for e in measured) / len(measured)
                if measured
                else None
            )
            scores[model.id] = score(
                model.id,
                task.category,
                evaluations,
                weights,
                cost=estimate(model, request),
                project=request.project,
                reliability=reliability,
                latency=latency,
            )
        eligible = [
            m for m in eligible if scores[m.id]["confidence"] >= policy.min_confidence
        ]
        if not eligible:
            raise ValueError("insufficient evaluation confidence")
        use_scores = self.config.ris_enabled and any(
            s["samples"] for s in scores.values()
        )

        def key(model: Model) -> tuple[float, float, str]:
            if use_scores:
                return -float(scores[model.id]["score"]), -model.priority, model.id
            cost = estimate(model, request)
            price = cost if cost is not None else float("inf")
            if profile == "economy":
                return price, -model.priority, model.id
            return -model.priority, price, model.id

        selected = min(eligible, key=key)
        shadow_model = None
        if request.shadow:
            shadow_model = selected.id
            original = self.registry.get(request.model or "")
            reasons = rejection_reasons(original, request, policy, task)
            if reasons:
                raise ValueError("shadow original ineligible: " + "; ".join(reasons))
            selected = original
        decision = Decision(
            model_id=selected.id,
            shadow_model=shadow_model,
            scores=scores,
            policy_version=policy_version,
            provider=selected.provider,
            project=request.project,
            profile=profile,
            classification=task,
            reasoning=effort_for(selected, request, task),
            estimated_cost=estimate(selected, request),
            classifier_estimated_cost=classifier_cost,
            estimated_input_tokens=input_tokens(request),
            reasons=[
                "mandatory filters passed",
                "evidence-based RIS"
                if use_scores
                else "operator priority; insufficient quality evidence",
                "token estimate is a conservative byte bound",
            ],
            rejected=rejected,
        )
        logger.info(
            "routing decision=%s provider=%s dry_run=%s",
            decision.id,
            selected.provider,
            request.dry_run,
        )
        if request.dry_run:
            return RouteResult(decision=decision)
        if request.stream:
            raise ValueError("use stream() for streaming requests")
        candidates = [selected]
        if (
            policy.allow_fallback
            and not request.model
            and not policy.model
            and not request.shadow
        ):
            candidates += sorted(
                (
                    m
                    for m in eligible
                    if m.id != selected.id
                    and (
                        m.provider == selected.provider
                        or policy.cross_provider_fallback
                    )
                ),
                key=key,
            )
        last_error: ValueError | None = None
        for index, candidate in enumerate(candidates):
            try:
                response = await self._complete(candidate, request, task)
            except ValueError as exc:
                last_error = exc
                continue
            decision.model_id, decision.provider = candidate.id, candidate.provider
            decision.estimated_cost = estimate(candidate, request)
            decision.reasoning = effort_for(candidate, request, task)
            decision.fallbacks = index
            if request.session:
                self.sessions[(request.project, request.session)] = candidate.id
                if len(self.sessions) > self.config.cache_capacity:
                    self.sessions.popitem(last=False)
            self.state.record(
                {
                    "id": decision.id,
                    "project": request.project,
                    "model": candidate.id,
                    "provider": candidate.provider,
                    "status": "decision",
                    "category": task.category,
                    "complexity": task.complexity,
                    "fallbacks": index,
                    "shadow_model": shadow_model,
                    "policy_version": decision.policy_version,
                    "scores": scores,
                }
            )
            return RouteResult(decision=decision, response=response)
        raise last_error or ValueError("no available provider")

    async def stream(
        self, prompt: str, **options: Any
    ) -> AsyncGenerator[dict[str, Any]]:
        from zittomind.providers.streaming import stream

        options.pop("dry_run", None)
        options["stream"] = True
        request = Request(prompt=prompt, **options)
        options["operation_id"] = request.operation_id
        result = await self.route(prompt, **options, dry_run=True)
        model = self.registry.get(result.decision.model_id)
        credentials = Credentials()
        secret = (
            credentials.openai_api_key
            if model.provider == "openai"
            else credentials.anthropic_api_key
        )
        if not secret and model.provider != "ollama":
            raise ValueError("missing provider credential")
        params = reasoning_parameters(
            model, result.decision.reasoning, request.max_output_tokens
        )
        created = int(time.time())
        async with aclosing(
            self.execution.stream(
                model,
                request,
                self.config.projects[request.project],
                lambda: (
                    ollama.stream(model, request, self.config.timeout_seconds)
                    if model.provider == "ollama"
                    else stream(
                        model,
                        request,
                        params,
                        secret.get_secret_value() if secret else "",
                        self.config.timeout_seconds,
                    )
                ),
            )
        ) as events:
            async for event in events:
                if event.get("usage"):
                    usage = event["usage"]
                    usage["total_tokens"] = usage.get("prompt_tokens", 0) + usage.get(
                        "completion_tokens", 0
                    )
                yield {
                    "id": result.decision.id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model.id,
                    **event,
                }
        if request.session:
            self.sessions[(request.project, request.session)] = model.id
            if len(self.sessions) > self.config.cache_capacity:
                self.sessions.popitem(last=False)
        self.state.record(
            {
                "id": result.decision.id,
                "project": request.project,
                "model": model.id,
                "provider": model.provider,
                "status": "decision",
                "category": result.decision.classification.category,
                "complexity": result.decision.classification.complexity,
                "policy_version": result.decision.policy_version,
                "shadow_model": result.decision.shadow_model,
            }
        )

    async def simulate(
        self, prompt: str, *, version: int, **options: Any
    ) -> RouteResult:
        versions = [v for v in self.history.versions() if v["version"] == version]
        if not versions:
            raise ValueError("unknown policy version")
        configuration = self.config.model_copy(deep=True)
        configuration.profiles["simulation"] = versions[0]["weights"]
        configuration.adaptive_enabled = False
        # A separate instance avoids mutating routing policy for concurrent callers.
        candidate = ZittoMind(configuration)
        if self.config.state_path == ":memory:":
            for evaluation in self.history.evaluations():
                candidate.history.feedback(evaluation)
        try:
            options.update(
                dry_run=True, external_classification=False, profile="simulation"
            )
            return await candidate.route(prompt, **options)
        finally:
            candidate.close()
