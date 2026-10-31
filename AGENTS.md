# Repository Guidelines

## Project Structure & Module Organization

The repository is currently specification-only: `README.md` identifies ZittoMind, `LICENSE` contains the license, and `PROMONT.md` describes the planned LLM routing system. No application code, tests, or assets exist yet. Read the relevant specification sections before implementing features.

The proposed layout uses `src/routemind/`: `core/` for routing, `providers/` for adapters, `cli/` and `api/` for entry points, and `services/` for budgets, cache, and metrics. Supporting directories are planned for `tests/`, `benchmarks/`, `examples/`, `docs/`, and `config/`. Keep routing independent of CLI and HTTP interfaces. The specification uses RouteMind identifiers despite the ZittoMind repository name; resolve naming consistently when establishing packaging.

## Build, Test, and Development Commands

No build, installation, or development commands are configured yet. Once packaging, dependencies, and source files exist, establish these intended checks:

- `python3 -m pytest`: run the test suite.
- `ruff check .`: lint Python code.
- `ruff format --check .`: check formatting.
- `mypy src/`: check type annotations.

Document verified installation and startup commands in `README.md` when implementation lands. Specification CLI examples are not currently executable.

## Coding Style & Naming Conventions

Target Python 3.11+ and Linux. Use four-space indentation, type hints, `snake_case` modules and functions, and `PascalCase` classes. Configure Ruff and mypy in `pyproject.toml` when introducing code. Use asynchronous I/O for provider requests and isolate provider-specific behavior in adapters.

## Testing Guidelines

The specification selects pytest, pytest-asyncio, and respx for HTTP mocks. Organize tests under `tests/unit/`, `integration/`, `regression/`, and `security/`; name files `test_*.py`. Cover routing eligibility, privacy policies, budgets, fallback, and provider failures. Unit tests must run without paid APIs. No coverage threshold is configured. Report checks actually executed and any blockers.

## Commit & Pull Request Guidelines

History contains only `Initial commit`, so no established commit convention exists. Use concise, imperative subjects and focused commits. PR descriptions should explain behavior changes, reference relevant specification sections or issues, list validation results, and identify incomplete features.

## Security & Configuration

Keep credentials out of version control and logs. Provide placeholders in `.env.example` when configuration is added. Preserve local-first behavior, avoid storing full prompts by default, and keep dry runs free of paid calls by default.
