"""Synchronous Mnemonic client."""
from __future__ import annotations

import os
from typing import Any

import httpx

from mnemonic.exceptions import AuthError, MnemonicError, NotFoundError, RateLimitError


def _raise_for(response: httpx.Response) -> None:
    if response.status_code == 401:
        raise AuthError(response.json().get("detail", "Invalid API key"))
    if response.status_code == 404:
        raise NotFoundError(response.json().get("detail", "Not found"))
    if response.status_code == 429:
        raise RateLimitError(response.json().get("detail", "Rate limited"))
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail")
        except Exception:
            detail = response.text
        raise MnemonicError(f"HTTP {response.status_code}: {detail}")


class Mnemonic:
    """
    Synchronous Mnemonic client.

    Two SDK calls bracket every agent invocation:
      • ``recall(...)`` before the task
      • ``capture(...)`` after the task

    Example:
        >>> from mnemonic import Mnemonic
        >>> m = Mnemonic(api_key="mnemo_sk_...")
        >>> ctx = m.recall(agent_id="coder-7", task="fix jwt", as_prompt=True)
        >>> # ... run your agent with ctx injected ...
        >>> m.capture(agent_id="coder-7", task="fix jwt", actions=[],
        ...           output="patched", success=True)
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://mnemonic-production.up.railway.app/api",
        timeout: float = 30.0,
    ) -> None:
        self.api_key = (
            api_key
            or os.environ.get("MNEMONIC_API_KEY")
            or os.environ.get("MNEMO_API_KEY")
        )
        if not self.api_key:
            raise ValueError(
                "API key required. Pass api_key= or set MNEMONIC_API_KEY env var."
            )
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "mnemonic-python/0.2.0",
            },
            timeout=timeout,
        )

    # ------------------------------------------------------------------ recall
    def recall(
        self,
        agent_id: str,
        task: str,
        limit: int = 5,
        context: dict[str, Any] | None = None,
        as_prompt: bool = False,
    ) -> dict | str:
        """Retrieve relevant lessons and procedures before running an agent task.

        Args:
            agent_id: Your agent's identifier.
            task: Description of the task the agent is about to perform.
            limit: Max number of lessons to retrieve (default 5).
            context: Optional dict of environment metadata to improve routing
                     e.g. {"framework": "react", "language": "typescript"}.
            as_prompt: If True, returns a formatted string ready to inject into
                       the agent's system prompt instead of a structured dict.

        Returns:
            RecallResponse dict (or formatted string if as_prompt=True).

        Example:
            >>> lessons = m.recall(
            ...     agent_id="frontend-agent",
            ...     task="fix React context rerender storm",
            ...     context={"framework": "react", "runtime": "production"},
            ... )
            >>> for lesson in lessons["lessons"]:
            ...     print(lesson["problem_signature"], lesson["root_cause"])
        """
        payload: dict[str, Any] = {
            "agent_id": agent_id,
            "task": task,
            "limit": limit,
        }
        if context:
            payload["context"] = context
        if as_prompt:
            payload["as_prompt"] = True

        r = self._client.post("/v1/recall", json=payload)
        _raise_for(r)
        data = r.json()
        if as_prompt:
            return data.get("context_prompt") or ""
        return data

    # ----------------------------------------------------------------- capture
    def capture(
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
        """Capture an agent execution so Mnemonic can learn from it.

        Reflection runs asynchronously on the server — this call returns
        immediately.

        Args:
            agent_id: Your agent's identifier.
            task: The task that was performed.
            actions: List of actions the agent took, e.g.
                     [{"type": "tool_call", "target": "bash", "result": "ok"}].
            output: Final output or summary from the agent.
            success: Whether the task succeeded.
            time_taken: Duration in milliseconds (optional).
            retries: Number of retries needed (default 0).
            metadata: Any additional context to store.

        Returns:
            {"event_id": "...", "status": "captured", "reflection_queued": True}
        """
        r = self._client.post(
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

    # ---------------------------------------------------------- agent helpers
    def create_agent(
        self,
        external_id: str,
        name: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        """Create or register an agent."""
        r = self._client.post(
            "/v1/agents",
            json={
                "external_id": external_id,
                "name": name,
                "description": description,
                "metadata": metadata or {},
            },
        )
        _raise_for(r)
        return r.json()

    def list_agents(self) -> list[dict]:
        r = self._client.get("/v1/agents")
        _raise_for(r)
        return r.json()

    def agent_stats(self, agent_id: str) -> dict:
        r = self._client.get(f"/v1/agents/{agent_id}/stats")
        _raise_for(r)
        return r.json()

    def list_lessons(self, agent_id: str | None = None, limit: int = 50) -> list[dict]:
        params: dict[str, Any] = {"limit": limit}
        if agent_id:
            params["agent_id"] = agent_id
        r = self._client.get("/v1/lessons", params=params)
        _raise_for(r)
        return r.json()

    def list_procedures(self, agent_id: str | None = None) -> list[dict]:
        params: dict[str, Any] = {}
        if agent_id:
            params["agent_id"] = agent_id
        r = self._client.get("/v1/procedures", params=params)
        _raise_for(r)
        return r.json()

    # ---------------------------------------------------------- feedback
    def submit_feedback(
        self,
        rating: str,
        lesson_id: str | None = None,
        procedure_id: str | None = None,
        comment: str | None = None,
    ) -> dict:
        r = self._client.post(
            "/v1/feedback",
            json={
                "lesson_id": lesson_id,
                "procedure_id": procedure_id,
                "rating": rating,
                "comment": comment,
            },
        )
        _raise_for(r)
        return r.json()

    # ---------------------------------------------------------- analytics
    def report_lesson_effectiveness(
        self,
        lesson_id: str,
        agent_id: str,
        task: str,
        outcome: str,  # 'success' | 'failure' | 'partial'
        improvement_metrics: dict[str, Any] | None = None,
    ) -> dict:
        """Report how using a lesson affected task outcome."""
        r = self._client.post(
            "/v1/analytics/lesson-effectiveness",
            json={
                "lesson_id": lesson_id,
                "agent_id": agent_id,
                "task": task,
                "outcome": outcome,
                "improvement_metrics": improvement_metrics or {},
            },
        )
        _raise_for(r)
        return r.json()

    def get_lesson_analytics(self, lesson_id: str) -> dict:
        r = self._client.get(f"/v1/analytics/lesson/{lesson_id}")
        _raise_for(r)
        return r.json()

    def get_network_effects_stats(self) -> dict:
        r = self._client.get("/v1/analytics/network-effects")
        _raise_for(r)
        return r.json()

    # ---------------------------------------------------------------- cleanup
    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "Mnemonic":
        return self

    def __exit__(self, *_args) -> None:
        self.close()
