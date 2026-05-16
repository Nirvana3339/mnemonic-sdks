"""
Mnemonic OpenAI integration.

Two modes:
  1. MnemoOpenAI — wraps a single chat completion with recall + capture
  2. MnemoOpenAISession — tracks a full multi-turn conversation,
     auto-captures on session end

Usage (single call):
    from openai import OpenAI
    from mnemo.integrations.openai import MnemoOpenAI

    m = MnemoOpenAI(mnemo_api_key="mnemo_sk_...", agent_id="my-agent",
                    openai_client=OpenAI(), context={"framework": "react"})

    response = m.run(task="Fix React context rerender storm",
                     system="You are a senior engineer.")

Usage (multi-turn session):
    with MnemoOpenAISession(mnemo_api_key="...", agent_id="agent",
                            openai_client=OpenAI(), task="Debug app") as s:
        reply = s.send("here are my bugs")
        reply = s.send("fix all")
        s.add_diff(patch)
    # auto-captures on exit
"""
from __future__ import annotations

import time
from typing import Any

from mnemo.client import Mnemo


class MnemoOpenAI:
    """Wraps a single OpenAI chat completion with recall + auto-capture."""

    def __init__(
        self,
        mnemo_api_key: str,
        agent_id: str,
        openai_client: Any,
        base_url: str | None = None,
        context: dict | None = None,
    ) -> None:
        self.mnemo = Mnemo(api_key=mnemo_api_key, base_url=base_url) if base_url else Mnemo(api_key=mnemo_api_key)
        self.agent_id = agent_id
        self.client = openai_client
        self.context = context or {}

    def build_messages(self, task: str, system: str = "") -> list[dict]:
        """Build messages with recalled lessons injected into the system message."""
        recalled = self.mnemo.recall(
            agent_id=self.agent_id,
            task=task,
            as_prompt=True,
            context=self.context,
        )
        full_system = f"{system}\n\n{recalled}" if recalled and system else (recalled or system)
        msgs = []
        if full_system:
            msgs.append({"role": "system", "content": full_system})
        msgs.append({"role": "user", "content": task})
        return msgs

    def run(
        self,
        task: str,
        system: str = "",
        messages: list[dict] | None = None,
        model: str = "gpt-4o",
        **kwargs,
    ) -> Any:
        """
        Full recall → run → capture cycle in one call.

        Example:
            response = mnemo_openai.run(
                task="Fix the React context rerender storm",
                system="You are a senior React engineer.",
            )
        """
        if messages is None:
            messages = self.build_messages(task, system)

        t0 = time.time()
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )
        time_taken = int((time.time() - t0) * 1000)

        choice = response.choices[0] if response.choices else None
        output = choice.message.content if choice else ""

        conversation = messages + [{"role": "assistant", "content": output}]

        self.mnemo.capture(
            agent_id=self.agent_id,
            task=task,
            output=output or "",
            time_taken=time_taken,
            context=self.context,
            conversation=conversation,
            metadata={"model": getattr(response, "model", model)},
        )
        return response

    def capture_completion(
        self,
        task: str,
        response: Any,
        success: bool | None = None,
        conversation: list[dict] | None = None,
    ) -> dict:
        """Manually capture a completion you already have."""
        choice = response.choices[0] if getattr(response, "choices", None) else None
        output = choice.message.content if choice else ""
        return self.mnemo.capture(
            agent_id=self.agent_id,
            task=task,
            output=output or "",
            success=success,
            context=self.context,
            conversation=conversation or [],
        )


class MnemoOpenAISession:
    """
    Tracks a full multi-turn OpenAI conversation.
    Auto-captures on session end — no manual calls needed.

    Example:
        with MnemoOpenAISession(
            mnemo_api_key="mnemo_sk_...",
            agent_id="debugger",
            openai_client=OpenAI(),
            task="Debug production React app",
            context={"framework": "react"},
        ) as session:
            session.send("Here are the bugs I found...")
            session.send("fix all")
            session.add_diff(patch_content)
        # Captures automatically on __exit__
    """

    def __init__(
        self,
        mnemo_api_key: str,
        agent_id: str,
        openai_client: Any,
        task: str,
        system: str = "",
        model: str = "gpt-4o",
        context: dict | None = None,
        base_url: str | None = None,
    ) -> None:
        self.mnemo = Mnemo(api_key=mnemo_api_key, base_url=base_url) if base_url else Mnemo(api_key=mnemo_api_key)
        self.agent_id = agent_id
        self.client = openai_client
        self.task = task
        self.model = model
        self.context = context or {}
        self._messages: list[dict] = []
        self._diffs: list[str] = []
        self._test_output: str | None = None
        self._start = time.time()
        self._ended = False

        # Recall lessons and inject into system prompt
        recalled = self.mnemo.recall(
            agent_id=agent_id, task=task, as_prompt=True, context=self.context,
        )
        full_system = f"{system}\n\n{recalled}" if recalled and system else (recalled or system)
        if full_system:
            self._messages.append({"role": "system", "content": full_system})

    def send(self, user_message: str) -> str:
        """Send a user message and get a response. Full history tracked."""
        self._messages.append({"role": "user", "content": user_message})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._messages,
        )
        assistant_text = response.choices[0].message.content if response.choices else ""
        self._messages.append({"role": "assistant", "content": assistant_text})
        return assistant_text

    def add_diff(self, diff: str) -> None:
        """Record a code diff — strong success signal for outcome inference."""
        self._diffs.append(diff)

    def set_test_output(self, output: str) -> None:
        """Record test output — strongest success signal."""
        self._test_output = output

    def end(self) -> dict:
        """Capture the session. Called automatically by context manager."""
        if self._ended:
            return {}
        self._ended = True
        last_assistant = next(
            (m["content"] for m in reversed(self._messages) if m["role"] == "assistant"), ""
        )
        try:
            return self.mnemo.capture(
                agent_id=self.agent_id,
                task=self.task,
                output=last_assistant,
                time_taken=int((time.time() - self._start) * 1000),
                context=self.context,
                conversation=self._messages,
                code_diffs=self._diffs,
                test_output=self._test_output,
            )
        except Exception:
            return {}

    def __enter__(self) -> "MnemoOpenAISession":
        return self

    def __exit__(self, *_) -> None:
        self.end()
