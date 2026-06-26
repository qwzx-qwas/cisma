"""HTTP client helpers for secure aggregation services."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from secure_agg.exceptions import CommunicationError
from secure_agg.schemas.messages import AggregateShareMessage, ShareMessage


def _message_to_dict(message: object) -> dict[str, Any]:
    dump = getattr(message, "model_dump", None)
    if callable(dump):
        return dump()
    as_dict = getattr(message, "dict", None)
    if callable(as_dict):
        return as_dict()
    raise TypeError("message must provide model_dump() or dict()")


async def post_json(
    url: str,
    payload: dict,
    timeout_seconds: float = 10.0,
) -> dict:
    """Send a JSON POST request with bounded retries and clear errors."""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds, trust_env=False) as client:
                response = await client.post(url, json=payload)
            if response.status_code < 200 or response.status_code >= 300:
                raise CommunicationError(
                    f"POST {url} returned {response.status_code}: {response.text}"
                )
            data = response.json()
            if not isinstance(data, dict):
                raise CommunicationError(f"POST {url} returned non-object JSON")
            return data
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError, CommunicationError) as exc:
            last_error = exc
            if attempt == 2:
                break
            await asyncio.sleep(0.2 * (attempt + 1))
    raise CommunicationError(f"POST {url} failed after retries: {last_error}")


async def get_json(
    url: str,
    timeout_seconds: float = 10.0,
) -> dict:
    """Send a JSON GET request with bounded retries and clear errors."""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds, trust_env=False) as client:
                response = await client.get(url)
            if response.status_code < 200 or response.status_code >= 300:
                raise CommunicationError(
                    f"GET {url} returned {response.status_code}: {response.text}"
                )
            data = response.json()
            if not isinstance(data, dict):
                raise CommunicationError(f"GET {url} returned non-object JSON")
            return data
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError, CommunicationError) as exc:
            last_error = exc
            if attempt == 2:
                break
            await asyncio.sleep(0.2 * (attempt + 1))
    raise CommunicationError(f"GET {url} failed after retries: {last_error}")


async def send_share(
    target_base_url: str,
    message: ShareMessage,
) -> None:
    """Send one secret share message to a party service."""
    url = f"{target_base_url.rstrip('/')}/rounds/{message.round_id}/shares"
    await post_json(url, _message_to_dict(message))


async def send_aggregate_share(
    coordinator_base_url: str,
    message: AggregateShareMessage,
) -> None:
    """Send one aggregate share message to the coordinator."""
    url = f"{coordinator_base_url.rstrip('/')}/rounds/{message.round_id}/aggregate-shares"
    await post_json(url, _message_to_dict(message))


async def get_round_status(
    coordinator_base_url: str,
    round_id: str,
) -> dict:
    """Fetch a coordinator round result or status document."""
    url = f"{coordinator_base_url.rstrip('/')}/rounds/{round_id}/result"
    return await get_json(url)
