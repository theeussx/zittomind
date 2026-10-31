"""Public asynchronous SDK. Decisions never include prompt text."""

import logging
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
from zittomind.providers import anthropic, openai
from zittomind.schemas import (
    Classification,
    Completion,
    Decision,
    Model,
    Policy,
    Request,
    RouteResult,
)

logger = logging.getLogger("zittomind")


class ZittoMind:
    def __init__(self, config: Config | None = None):
        self.config = (config or load_config()).model_copy(deep=True)
        self.registry = Registry(self.config.models)

    async def _complete(
        self, model: Model, request: Request, task: Classification
    ) -> Completion:
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
        response = await self._complete(model, probe, task)
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
        task = classify(request)
        classifier_cost = 0.0
        if request.external_classification and task.confidence < 0.75:
            task, classifier_cost = await self._external(request, policy, task)
            if policy.max_cost_per_request is not None:
                policy.max_cost_per_request = max(
                    0, policy.max_cost_per_request - classifier_cost
                )
        rejected: dict[str, list[str]] = {}
        eligible = []
        for model in self.registry.models.values():
            reasons = rejection_reasons(model, request, policy, task)
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

        def key(model: Model) -> tuple[float, float, str]:
            cost = estimate(model, request)
            price = cost if cost is not None else float("inf")
            if profile == "economy":
                return price, -model.priority, model.id
            return -model.priority, price, model.id

        selected = min(eligible, key=key)
        decision = Decision(
            model_id=selected.id,
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
                "operator priority and estimated cost; no measured RIS",
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
        response = (
            None if request.dry_run else await self._complete(selected, request, task)
        )
        return RouteResult(decision=decision, response=response)

    async def stream(
        self, prompt: str, **options: Any
    ) -> AsyncGenerator[dict[str, Any]]:
        from zittomind.providers.streaming import stream

        options.pop("dry_run", None)
        options["stream"] = True
        result = await self.route(prompt, **options, dry_run=True)
        request = Request(prompt=prompt, **options)
        model = self.registry.get(result.decision.model_id)
        credentials = Credentials()
        secret = (
            credentials.openai_api_key
            if model.provider == "openai"
            else credentials.anthropic_api_key
        )
        if not secret:
            raise ValueError("missing provider credential")
        params = reasoning_parameters(
            model, result.decision.reasoning, request.max_output_tokens
        )
        async with aclosing(
            stream(
                model,
                request,
                params,
                secret.get_secret_value(),
                self.config.timeout_seconds,
            )
        ) as events:
            async for event in events:
                yield {
                    "id": result.decision.id,
                    "object": "chat.completion.chunk",
                    "model": model.id,
                    **event,
                }
