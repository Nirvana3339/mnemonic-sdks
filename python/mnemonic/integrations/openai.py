"""Drop-in helper that injects Mnemo recall into OpenAI Chat Completion calls."""
from __future__ import annotations

from typing import Any

from mnemonic.client import Mnemo


class MnemoOpenAI:
    def __init__(self, api_key: str, agent_id: str, openai_client: Any, base_url: str | None = None) -> None:
        self.mnemo = Mnemo(api_key=api_key, base_url=base_url) if base_url else Mnemo(api_key=api_key)
        self.agent_id = agent_id
        self.client = openai_client

    def build_messages(self, task: str, system: str) -> list[dict]:
        ctx = self.mnemo.recall(agent_id=self.agent_id, task=task, as_prompt=True)
        full_system = f"{system}\n\n{ctx}" if ctx else system
        return [
            {"role": "system", "content": full_system},
            {"role": "user", "content": task},
        ]

    def capture_completion(self, task: str, response: Any, success: bool) -> dict:
        choice = response.choices[0] if getattr(response, "choices", None) else None
        output = choice.message.content if choice else ""
        tokens = response.usage.total_tokens if getattr(response, "usage", None) else None
        return self.mnemo.capture(
            agent_id=self.agent_id,
            task=task,
            actions=[{"type": "llm_call", "target": getattr(response, "model", "openai"),
                      "result": f"{tokens} tokens" if tokens else "ok"}],
            output=output or "",
            success=success,
            metadata={"model": getattr(response, "model", "openai"), "tokens": tokens},
        )
