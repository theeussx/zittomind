"""Run from the repository root; no network or credentials required."""

import asyncio
from pathlib import Path

from zittomind import ZittoMind
from zittomind.config import load_config


async def main() -> None:
    router = ZittoMind(load_config(Path("config/offline-example.yaml")))
    result = await router.route("Explique o comando chmod", dry_run=True)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
