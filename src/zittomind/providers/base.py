"""HTTP boundary: fixed destinations, no redirects or automatic retries."""

from typing import Any

import httpx


async def post(
    url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float
) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=False, trust_env=False
        ) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("invalid response")
            return data
    except httpx.HTTPStatusError as exc:
        raise ValueError(
            f"provider HTTP {exc.response.status_code}; no automatic retry"
        ) from None
    except (httpx.HTTPError, ValueError):
        raise ValueError("provider transport or response failure") from None
