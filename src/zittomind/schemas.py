"""Validated public contracts; payloads never carry internal policy."""

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

Complexity = Literal["SIMPLE", "MEDIUM", "ADVANCED"]
Effort = Literal["low", "medium", "high"]
Profile = Literal["economy", "balanced", "performance"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Message(Contract):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=100000)


class Request(Contract):
    prompt: str = Field(min_length=1, max_length=100000)
    messages: list[Message] = Field(default_factory=list, max_length=100)
    project: str = "default"
    profile: Profile | None = None
    model: str | None = None
    provider: Literal["openai", "anthropic"] | None = None
    reasoning: Effort | None = None
    complexity: Complexity | None = None
    max_output_tokens: int = Field(default=1024, ge=1, le=100000)
    dry_run: bool = False
    local_only: bool = False
    stream: bool = False
    tools: bool = False
    structured_output: bool = False
    external_classification: bool = False

    @field_validator("prompt")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("empty prompt")
        return value


class Classification(Contract):
    complexity: Complexity
    confidence: float = Field(ge=0, le=1)
    category: str = Field(max_length=100)
    reasoning_requirement: Effort
    context_dependency: bool = False
    tool_dependency: bool = False
    accuracy_sensitivity: Literal["normal", "high"] = "normal"
    estimated_output_size: Literal["short", "long"] = "short"


class Model(Contract):
    id: str = Field(min_length=1, max_length=200)
    provider: Literal["openai", "anthropic"]
    enabled: bool = True
    context_window: int | None = Field(default=None, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    input_per_million: float | None = Field(default=None, ge=0)
    output_per_million: float | None = Field(default=None, ge=0)
    priority: int = Field(default=50, ge=0, le=100)
    tier: Complexity = "ADVANCED"
    reasoning_mode: Literal[
        "none", "openai_effort", "anthropic_budget", "anthropic_adaptive"
    ] = "none"
    supported_efforts: list[Effort] = Field(default_factory=list)
    thinking_budgets: dict[Effort, int] = Field(default_factory=dict)
    output_parameter: Literal["max_tokens", "max_completion_tokens"] = (
        "max_completion_tokens"
    )


class Policy(Contract):
    profile: Profile = "balanced"
    privacy: Literal["standard", "strict"] = "standard"
    max_cost_per_request: float | None = Field(default=None, ge=0)
    allowed_providers: list[Literal["openai", "anthropic"]] = Field(
        default=["openai", "anthropic"]
    )
    model: str | None = None
    external_classification: bool = False
    classifier_model: str | None = None
    classifier_max_cost: float = Field(default=0.001, gt=0)


class Decision(Contract):
    id: str = Field(default_factory=lambda: uuid4().hex)
    model_id: str
    provider: str
    project: str
    profile: Profile
    classification: Classification
    reasoning: Effort | None
    estimated_cost: float | None
    classifier_estimated_cost: float = 0
    estimated_input_tokens: int
    reasons: list[str]
    rejected: dict[str, list[str]]
    policy_version: str = "rules-v1"


class Completion(Contract):
    text: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    finish_reason: str | None = None


class RouteResult(Contract):
    decision: Decision
    response: Completion | None = None
