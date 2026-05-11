"""Drop-in helper that injects Mnemo recall into Anthropic Claude calls."""
from __future__ import annotations

import time
from typing import Any

from mnemo.client import Mnemo


class MnemoClaude:
    def __init__(self, api_key: str, agent_id: str, claude_client: Any, base_url: str | None = None) -> None:
        self.mnemo = Mnemo(api_key=api_key, base_url=base_url) if base_url else Mnemo(api_key=api_key)
        self.agent_id = agent_id
        self.client = claude_client

    def build_system(self, base_system: str, task: str) -> str:
        ctx = self.mnemo.recall(agent_id=self.agent_id, task=task, as_prompt=True)
        return f"{base_system}\n\n{ctx}" if ctx else base_system

    def capture_response(
        self,
        task: str,
        response: Any,
        success: bool,
        time_taken: int | None = None,
    ) -> dict:
        output = response.content[0].text if getattr(response, "content", None) else ""
        tokens = (
            response.usage.input_tokens + response.usage.output_tokens
            if getattr(response, "usage", None)
            else None
        )
        return self.mnemo.capture(
            agent_id=self.agent_id,
            task=task,
            actions=[{"type": "llm_call", "target": getattr(response, "model", "claude"),
                      "result": f"{tokens} tokens" if tokens else "ok"}],
            output=output,
            success=success,
            time_taken=time_taken,
            metadata={"model": getattr(response, "model", "claude"), "tokens": tokens},
        )
