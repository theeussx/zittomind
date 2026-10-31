"""Thin CLI over the SDK; failures never print validation input values."""

import asyncio
import json
from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from pydantic import ValidationError

from zittomind import ZittoMind
from zittomind.config import Config, Credentials, load_config
from zittomind.core.classifier import classify as classify_request
from zittomind.schemas import Request

app = typer.Typer(
    help="ZittoMind — local-first LLM routing", pretty_exceptions_enable=False
)
ConfigPath = Annotated[Path | None, typer.Option("--config")]


def read_config(path: Path | None) -> Config:
    try:
        return load_config(path)
    except (OSError, ValueError, yaml.YAMLError):
        typer.echo(
            "Invalid or unreadable configuration; check schema and file permissions.",
            err=True,
        )
        raise typer.Exit(2) from None


def emit(data: Any) -> None:
    typer.echo(json.dumps(data, ensure_ascii=False, indent=2))


@app.command()
def init(path: Path = Path("zittomind.yaml")) -> None:
    """Create an empty registry without replacing an existing file."""
    try:
        with path.open("x") as handle:
            yaml.safe_dump(
                Config(state_path=".zittomind/state.sqlite3").model_dump(), handle
            )
    except OSError:
        typer.echo(
            "Cannot create configuration (file exists or path unavailable).", err=True
        )
        raise typer.Exit(2) from None
    typer.echo(f"Created {path}; configure models before asking.")


@app.command("classify")
def classify_command(
    prompt: str, json_output: Annotated[bool, typer.Option("--json")] = False
) -> None:
    """Classify locally, without credentials or network."""
    try:
        result = classify_request(Request(prompt=prompt))
    except ValidationError:
        typer.echo("Invalid request.", err=True)
        raise typer.Exit(2) from None
    if json_output:
        emit(result.model_dump())
    else:
        typer.echo(f"{result.complexity} (heuristic confidence: {result.confidence})")


@app.command()
def models(config: ConfigPath = None) -> None:
    emit([m.model_dump() for m in read_config(config).models])


@app.command("config")
def config_command(config: ConfigPath = None) -> None:
    """Validate and export configuration (never credentials)."""
    emit(read_config(config).model_dump())


@app.command()
def doctor(config: ConfigPath = None) -> None:
    settings = read_config(config)
    credentials = Credentials()
    emit(
        {
            "models_configured": len(settings.models),
            "openai_key_present": bool(credentials.openai_api_key),
            "anthropic_key_present": bool(credentials.anthropic_api_key),
            "network_checked": False,
        }
    )


@app.command()
def ask(
    prompt: str,
    config: ConfigPath = None,
    model: str | None = None,
    provider: str | None = None,
    profile: str | None = None,
    project: str = "default",
    reasoning: str | None = None,
    complexity: str | None = None,
    max_output_tokens: int = 1024,
    dry_run: bool = False,
    no_cache: bool = False,
    shadow: bool = False,
    session: str | None = None,
    local_only: bool = False,
    external_classification: bool = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Generate or inspect routing with --dry-run."""
    router = ZittoMind(read_config(config))
    try:
        result = asyncio.run(
            router.route(
                prompt,
                model=model,
                provider=provider,
                profile=profile,
                project=project,
                reasoning=reasoning,
                complexity=complexity,
                max_output_tokens=max_output_tokens,
                dry_run=dry_run,
                no_cache=no_cache,
                shadow=shadow,
                session=session,
                local_only=local_only,
                external_classification=external_classification,
            )
        )
    except ValidationError:
        typer.echo("Invalid request options.", err=True)
        raise typer.Exit(2) from None
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from None
    if json_output or dry_run:
        emit(result.model_dump())
    elif result.response:
        typer.echo(result.response.text)


@app.command()
def serve(
    config: ConfigPath = None,
    host: str = "127.0.0.1",
    port: int = 8787,
    project: str = "default",
) -> None:
    """Serve authenticated HTTP. Set ZITTOMIND_PROXY_TOKEN first."""
    import uvicorn

    from zittomind.api.app import create_app

    try:
        application = create_app(read_config(config), project=project)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from None
    uvicorn.run(application, host=host, port=port, access_log=False)


@app.command()
def stats(
    config: ConfigPath = None, project: str | None = None, csv: bool = False
) -> None:
    """Export recorded metadata or aggregate statistics; no prompts are retained."""
    import csv as csv_module
    import io

    from zittomind.services.state import State

    settings = read_config(config)
    state = State(settings.state_path)
    try:
        if csv:
            rows = state.events(project)
            output = io.StringIO()
            fields = sorted({key for row in rows for key in row})
            writer = csv_module.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
            typer.echo(output.getvalue())
        else:
            emit(state.stats(project))
    finally:
        state.close()


@app.command()
def projects(config: ConfigPath = None) -> None:
    emit(
        {
            name: policy.model_dump()
            for name, policy in read_config(config).projects.items()
        }
    )


@app.command()
def cache(config: ConfigPath = None) -> None:
    """Inspect cache policy. Runtime cache invalidation is available via HTTP."""
    settings = read_config(config)
    emit(
        {
            "storage": "process-memory",
            "ttl": settings.cache_ttl,
            "capacity": settings.cache_capacity,
            "response_cache_projects": [
                p for p, policy in settings.projects.items() if policy.response_cache
            ],
        }
    )


@app.command()
def benchmark(config: ConfigPath = None) -> None:
    """Run labeled offline fixtures; reports no invented generation quality."""
    from zittomind.services.benchmark import compare

    router = ZittoMind(read_config(config))
    try:
        emit(asyncio.run(compare(router)))
    except ValueError:
        typer.echo("Configure a registry for the offline benchmark.", err=True)
        raise typer.Exit(2) from None
    finally:
        router.close()


policies_app = typer.Typer(
    help="Inspect, version, simulate and roll back scoring policies."
)
app.add_typer(policies_app, name="policies")


@policies_app.command("list")
def policies_list(config: ConfigPath = None) -> None:
    router = ZittoMind(read_config(config))
    try:
        emit(router.history.versions())
    finally:
        router.close()


@policies_app.command("import")
def policies_import(path: Path, config: ConfigPath = None) -> None:
    router = ZittoMind(read_config(config))
    try:
        emit({"version": router.history.save(json.loads(path.read_text()))})
    except (ValueError, OSError):
        typer.echo("Invalid scoring policy.", err=True)
        raise typer.Exit(2) from None
    finally:
        router.close()


@policies_app.command("rollback")
def policies_rollback(version: int, config: ConfigPath = None) -> None:
    router = ZittoMind(read_config(config))
    try:
        router.history.activate(version)
        emit(router.history.active())
    except ValueError:
        typer.echo("Unknown policy version.", err=True)
        raise typer.Exit(2) from None
    finally:
        router.close()


@policies_app.command("simulate")
def policies_simulate(
    version: int, prompt: str = "Explique chmod", config: ConfigPath = None
) -> None:
    router = ZittoMind(read_config(config))
    try:
        emit(asyncio.run(router.simulate(prompt, version=version)).model_dump())
    except ValueError:
        typer.echo("Simulation failed; check policy and registry.", err=True)
        raise typer.Exit(2) from None
    finally:
        router.close()


@policies_app.command("feedback")
def feedback(
    model: str,
    quality: float,
    category: str = "general",
    project: str = "default",
    config: ConfigPath = None,
) -> None:
    from zittomind.services.adaptive import Evaluation

    router = ZittoMind(read_config(config))
    try:
        router.registry.get(model)
        if project not in router.config.projects:
            raise ValueError("unknown project")
        emit(
            {
                "evaluation": router.history.feedback(
                    Evaluation(
                        model=model, category=category, quality=quality, project=project
                    )
                )
            }
        )
    except ValueError:
        typer.echo("Invalid feedback.", err=True)
        raise typer.Exit(2) from None
    finally:
        router.close()


@policies_app.command("learn")
def policies_learn(project: str = "default", config: ConfigPath = None) -> None:
    router = ZittoMind(read_config(config))
    try:
        emit(
            {
                "proposed_version": router.history.learn(project=project),
                "activated": False,
            }
        )
    except ValueError:
        typer.echo("At least five explicit evaluations are required.", err=True)
        raise typer.Exit(2) from None
    finally:
        router.close()
