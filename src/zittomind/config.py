"""Configuration is trusted operator input, never generated from prompts."""

from pathlib import Path

import yaml
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from zittomind.schemas import Contract, Model, Policy


class Credentials(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None


class Config(Contract):
    models: list[Model] = Field(default_factory=list)
    projects: dict[str, Policy] = Field(default_factory=lambda: {"default": Policy()})
    state_path: str = ":memory:"
    concurrency: int = Field(default=8, ge=1, le=256)
    requests_per_minute: int = Field(default=60, ge=1)
    cache_ttl: float = Field(default=300, gt=0)
    cache_capacity: int = Field(default=256, ge=1, le=10000)
    retention_days: int = Field(default=30, ge=0)
    timeout_seconds: float = Field(default=30, gt=0, le=300)

    @model_validator(mode="after")
    def unique_models(self) -> "Config":
        if len({m.id for m in self.models}) != len(self.models):
            raise ValueError("duplicate model IDs")
        for m in self.models:
            if m.reasoning_mode.startswith("anthropic") and m.provider != "anthropic":
                raise ValueError("reasoning/provider mismatch")
            if m.reasoning_mode == "openai_effort" and m.provider != "openai":
                raise ValueError("reasoning/provider mismatch")
            if any(v < 1024 for v in m.thinking_budgets.values()):
                raise ValueError("thinking budgets must be at least 1024")
        return self


def load_config(path: Path | None = None) -> Config:
    target = path or Path("zittomind.yaml")
    if not target.exists() and path is None:
        return Config()
    if target.stat().st_size > 1000000:
        raise ValueError("configuration too large")
    return Config.model_validate(yaml.safe_load(target.read_text()) or {})
