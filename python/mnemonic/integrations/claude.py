"""
Mnemonic integration for Anthropic Claude.

Two modes:
  1. MnemoClaude — wraps a single Claude call with recall + auto-capture
  2. MnemoClaudeSession — tracks a full multi-turn conversation,
     auto-captures on session end with full conversation history
"""
from __future__ import annotations

import time
from typing import Any

from mnemo.client import Mnemo


class MnemoClaude:
    """Wraps a single Claude API call with recall before + capture after."""

    def __init__(
        self,
        api_key: str,
        agent_id: str,
        claude_client: Any,
        base_url: str | None = None,
        context: dict | None = None,
    ) -> None:
        self.mnemo = Mnemo(api_key=api_key, base_url=base_url) if base_url else Mnemo(api_key=api_key)
        self.agent_id = agent_id
        self.client = claude_client
        self.context = context or {}

    def build_system(self, base_system: str, task: str) -> str:
        """Inject recalled lessons into the system prompt."""
        ctx = self.mnemo.recall(
            agent_id=self.agent_id,
            task=task,
            as_prompt=True,
            context=self.context,
        )
        return f"{base_system}\n\n{ctx}" if ctx else base_system

    def run(
        self,
        task: str,
        system: str = "",
        messages: list[dict] | None = None,
        model: str = "claude-opus-4-7",
        max_tokens: int = 4096,
        **kwargs,
    ) -> Any:
        """
        Full recall → run → capture cycle in one call.

        Example:
            response = mnemoclaude.run(
                task="Fix the React context rerender storm",
                system="You are a senior React engineer.",
                messages=[{"role": "user", "content": user_input}],
            )
        """
        enriched_system = self.build_system(system, task)
        t0 = time.time()

        response = self.client.messages.create(
            model=model,
            system=enriched_system,
            messages=messages or [{"role": "user", "content": task}],
            max_tokens=max_tokens,
            **kwargs,
        )

        time_taken = int((time.time() - t0) * 1000)
        output = response.content[0].text if getattr(response, "content", None) else ""

        # Build conversation list for reflection
        conversation = (messages or [{"role": "user", "content": task}]) + [
            {"role": "assistant", "content": output}
        ]

        self.mnemo.capture(
            agent_id=self.agent_id,
            task=task,
            output=output,
            time_taken=time_taken,
            context=self.context,
            conversation=conversation,
            metadata={"model": getattr(response, "model", model)},
        )
        return response

    def capture_response(
        self,
        task: str,
        response: Any,
        success: bool | None = None,
        time_taken: int | None = None,
        conversation: list[dict] | None = None,
    ) -> dict:
        """Manually capture a response you already have."""
        output = response.content[0].text if getattr(response, "content", None) else ""
        return self.mnemo.capture(
            agent_id=self.agent_id,
            task=task,
            output=output,
            success=success,
            time_taken=time_taken,
            context=self.context,
            conversation=conversation or [],
        )


class MnemoClaudeSession:
    """
    Tracks a full multi-turn Claude conversation.
    Auto-captures the entire session when it ends — no manual calls needed.

    Usage:
        session = MnemoClaudeSession(
            mnemo_api_key="mnemo_sk_...",
            agent_id="my-agent",
            claude_client=anthropic.Anthropic(),
            task="Debug the React dashboard",
            context={"framework": "react", "language": "typescript"},
        )

        # Each turn — recall is injected on first message automatically
        response = session.send("My app freezes on websocket updates")
        response = session.send("fix all of them")

        # Session ends — full conversation captured, lessons extracted
        session.end()

        # Or use as context manager:
        with MnemoClaudeSession(...) as session:
            session.send("My app freezes...")
            session.send("fix all")
    """

    def __init__(
        self,
        mnemo_api_key: str,
        agent_id: str,
        claude_client: Any,
        task: str,
        system: str = "",
        model: str = "claude-opus-4-7",
        max_tokens: int = 4096,
        context: dict | None = None,
        base_url: str | None = None,
    ) -> None:
        self.mnemo = Mnemo(api_key=mnemo_api_key, base_url=base_url) if base_url else Mnemo(api_key=mnemo_api_key)
        self.agent_id = agent_id
        self.client = claude_client
        self.task = task
        self.model = model
        self.max_tokens = max_tokens
        self.context = context or {}
        self._messages: list[dict] = []
        self._diffs: list[str] = []
        self._test_output: str | None = None
        self._start = time.time()
        self._ended = False

        # Inject recalled lessons into system prompt on first message
        recalled = self.mnemo.recall(
            agent_id=agent_id,
            task=task,
            as_prompt=True,
            context=self.context,
        )
        self._system = f"{system}\n\n{recalled}" if recalled and system else (recalled or system)

    def send(self, user_message: str) -> str:
        """Send a user message, get assistant response. Conversation tracked automatically."""
        self._messages.append({"role": "user", "content": user_message})

        response = self.client.messages.create(
            model=self.model,
            system=self._system,
            messages=self._messages,
            max_tokens=self.max_tokens,
        )
        assistant_text = response.content[0].text if response.content else ""
        self._messages.append({"role": "assistant", "content": assistant_text})
        return assistant_text

    def add_diff(self, diff: str) -> None:
        """Record a code diff the agent produced — strong success signal."""
        self._diffs.append(diff)

    def set_test_output(self, output: str) -> None:
        """Record test/build output — strongest success signal."""
        self._test_output = output

    def end(self) -> dict:
        """Capture the full session. Called automatically by context manager."""
        if self._ended:
            return {}
        self._ended = True
        return self.mnemo.capture(
            agent_id=self.agent_id,
            task=self.task,
            output=self._messages[-1]["content"] if self._messages else "",
            time_taken=int((time.time() - self._start) * 1000),
            context=self.context,
            conversation=self._messages,
            code_diffs=self._diffs,
            test_output=self._test_output,
        )

    def __enter__(self) -> "MnemoClaudeSession":
        return self

    def __exit__(self, *_) -> None:
        self.end()
