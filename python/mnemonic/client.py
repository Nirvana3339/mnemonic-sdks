"""Synchronous Mnemo client."""
from __future__ import annotations

import os
from typing import Any

import httpx

from mnemonic.exceptions import AuthError, MnemoError, NotFoundError, RateLimitError


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
        raise MnemoError(f"HTTP {response.status_code}: {detail}")


class Mnemo:
    """
    Synchronous Mnemo client.

    Two SDK calls bracket every agent invocation:
      • ``recall(...)`` before
      • ``capture(...)`` after

    Example:
        >>> from mnemo import Mnemo
        >>> m = Mnemo(api_key="mnemo_sk_...")
        >>> ctx = m.recall(agent_id="coder-7", task="fix jwt", as_prompt=True)
        >>> m.capture(agent_id="coder-7", task="fix jwt", actions=[],
        ...           output="patched", success=True)
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.mnemo.dev",
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("MNEMO_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Pass api_key= or set MNEMO_API_KEY env var."
            )
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "mnemo-python/0.1.0",
            },
            timeout=timeout,
        )

    # ------------------------------------------------------------------ recall
    def recall(
        self,
        agent_id: str,
        task: str,
        limit: int = 5,
        min_confidence: float = 0.6,
        as_prompt: bool = False,
    ) -> dict | str:
        """Retrieve relevant lessons/procedures before running an agent task.

        If ``as_prompt=True`` returns a formatted string ready to inject into
        the agent's system prompt; otherwise returns a structured dict.
        """
        r = self._client.post(
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
        """Capture an agent execution. Returns immediately; reflection runs
        asynchronously on the server."""
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

    # ---------------------------------------------------------- helper methods
    def create_agent(
        self,
        external_id: str,
        name: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
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

    # -------------------------------------------------- network effects (v2)
    def report_lesson_effectiveness(
        self,
        lesson_id: str,
        agent_id: str,
        task: str,
        outcome: str,  # 'success' | 'failure' | 'partial'
        improvement_metrics: dict[str, Any] | None = None,
    ) -> dict:
        """Report how using a lesson affected task outcome.
        
        Enables network effect tracking:
        - Which lessons are most helpful
        - Success rates across different contexts
        - Attribution (which agents create valuable lessons)
        
        Args:
            lesson_id: ID of the lesson that was used
            agent_id: Agent that used the lesson
            task: The task that was performed
            outcome: 'success', 'failure', or 'partial'
            improvement_metrics: Optional metrics like:
                {
                    "time_saved_ms": 5000,
                    "retries_reduced": 2,
                    "errors_avoided": 1
                }
        
        Example:
            >>> lessons = m.recall(agent_id="agent-1", task="fix redis timeout")
            >>> # Agent uses lesson to fix issue
            >>> m.report_lesson_effectiveness(
            ...     lesson_id=lessons['lessons'][0]['id'],
            ...     agent_id="agent-1",
            ...     task="fix redis timeout",
            ...     outcome="success",
            ...     improvement_metrics={"time_saved_ms": 3600000, "retries_reduced": 3}
            ... )
        """
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
        """Get detailed analytics for a specific lesson.
        
        Returns:
            {
                "lesson_id": "...",
                "content": "...",
                "quality_score": 0.85,
                "usage_count": 42,
                "success_count": 38,
                "failure_count": 4,
                "success_rate": 0.90,
                "created_by_tenant_id": "...",
                "created_by_agent_id": "...",
                "reinforcement_count": 5,
                "contradiction_count": 0
            }
        
        Example:
            >>> analytics = m.get_lesson_analytics("lesson-uuid")
            >>> print(f"Quality: {analytics['quality_score']:.2f}")
            >>> print(f"Success rate: {analytics['success_rate']:.0%}")
        """
        r = self._client.get(f"/v1/analytics/lesson/{lesson_id}")
        _raise_for(r)
        return r.json()

    def get_network_effects_stats(self) -> dict:
        """Get global network effects statistics.
        
        Returns:
            {
                "total_lessons": 10523,
                "public_lessons": 8421,
                "private_lessons": 2102,
                "total_usage_events": 52341,
                "avg_quality_score": 0.73,
                "top_lessons": [...],
                "cross_tenant_learning_events": 15234
            }
        
        Shows how the global knowledge network is performing:
        - Total lessons in the system
        - Public vs private distribution
        - Top performing lessons
        - Cross-tenant learning metrics (network effects in action!)
        
        Example:
            >>> stats = m.get_network_effects_stats()
            >>> print(f"Network effects: {stats['cross_tenant_learning_events']} cross-tenant learnings!")
            >>> print(f"Top lesson: {stats['top_lessons'][0]['content']}")
        """
        r = self._client.get("/v1/analytics/network-effects")
        _raise_for(r)
        return r.json()

    # ---------------------------------------------------------------- cleanup
    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "Mnemo":
        return self

    def __exit__(self, *_args) -> None:
        self.close()
