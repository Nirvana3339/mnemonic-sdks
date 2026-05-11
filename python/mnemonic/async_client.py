"""Async Mnemo client."""
from __future__ import annotations

import os
from typing import Any

import httpx

from mnemo.client import _raise_for


class MnemoAsync:
    """Async sibling of :class:`Mnemo`. Same API, just awaitable."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.mnemo.dev",
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("MNEMO_API_KEY")
        if not self.api_key:
            raise ValueError("API key required.")
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "mnemo-python/0.1.0",
            },
            timeout=timeout,
        )

    async def recall(
        self,
        agent_id: str,
        task: str,
        limit: int = 5,
        min_confidence: float = 0.6,
        as_prompt: bool = False,
    ) -> dict | str:
        r = await self._client.post(
            "/v1/recall",
            json={
                "agent_id": agent_id,
                "task": task,
                "limit": limit,
                "min_confidence": min_confidence,
                "as_prompt": as_prompt,
            },
        )
        _raise_for(r)
        data = r.json()
        if as_prompt:
            return data.get("context_prompt") or ""
        return data

    async def capture(
        self,
        agent_id: str,
        task: str,
        actions: list[dict[str, Any]],
        output: str,
        success: bool,
        time_taken: int | None = None,
        retries: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        r = await self._client.post(
            "/v1/events",
            json={
                "agent_id": agent_id,
                "task": task,
                "actions": actions,
                "output": output,
                "success": success,
                "time_taken": time_taken,
                "retries": retries,
                "metadata": metadata or {},
            },
        )
        _raise_for(r)
        return r.json()

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "MnemoAsync":
        return self

    async def __aexit__(self, *_args) -> None:
        await self.close()
