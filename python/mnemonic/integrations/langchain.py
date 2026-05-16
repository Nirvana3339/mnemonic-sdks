"""
Mnemonic LangChain integration.

Two components:
  1. MnemoCallbackHandler — fires on agent_finish, captures full run automatically
  2. MnemoRecallTool — LangChain Tool that agents can use to recall lessons

Usage:
    from langchain_anthropic import ChatAnthropic
    from langchain.agents import AgentExecutor
    from mnemo.integrations.langchain import MnemoCallbackHandler, build_recall_context

    handler = MnemoCallbackHandler(
        mnemo_api_key="mnemo_sk_...",
        agent_id="my-langchain-agent",
        context={"framework": "react", "language": "typescript"},
    )

    # Inject recalled lessons into the system prompt before running
    system_prompt = build_recall_context(handler.mnemo, agent_id, task)

    executor = AgentExecutor(agent=agent, tools=tools, callbacks=[handler])
    executor.invoke({"input": task})
    # ↑ auto-captures on completion — no manual capture needed
"""
from __future__ import annotations

import time
from typing import Any, Union

from mnemo.client import Mnemo


def build_recall_context(
    mnemo: Mnemo,
    agent_id: str,
    task: str,
    context: dict | None = None,
) -> str:
    """Fetch recalled lessons as a prompt string to prepend to the system message."""
    try:
        return mnemo.recall(agent_id=agent_id, task=task, as_prompt=True, context=context or {}) or ""
    except Exception:
        return ""


class MnemoCallbackHandler:
    """
    LangChain callback handler that auto-captures every agent run.

    Hooks used:
      - on_chain_start  → record task + start time
      - on_agent_action → record tool calls as actions
      - on_agent_finish → capture full run with conversation
      - on_chain_error  → capture failure

    Compatible with: LangChain 0.1+, LangGraph agents, AgentExecutor.
    """

    def __init__(
        self,
        mnemo_api_key: str,
        agent_id: str,
        context: dict | None = None,
        base_url: str | None = None,
    ) -> None:
        self.mnemo = Mnemo(api_key=mnemo_api_key, base_url=base_url) if base_url else Mnemo(api_key=mnemo_api_key)
        self.agent_id = agent_id
        self.context = context or {}
        self._task: str = ""
        self._actions: list[dict] = []
        self._messages: list[dict] = []
        self._start: float = 0.0
        self._diffs: list[str] = []
        self._test_output: str | None = None

    # ── LangChain callback interface ────────────────────────────────────────

    def on_chain_start(self, serialized: dict, inputs: dict, **kwargs) -> None:
        self._task = inputs.get("input") or inputs.get("query") or str(inputs)[:200]
        self._start = time.time()
        self._actions = []
        self._messages = []
        if self._task:
            self._messages.append({"role": "user", "content": self._task})

    def on_agent_action(self, action: Any, **kwargs) -> None:
        self._actions.append({
            "type": "tool_call",
            "target": getattr(action, "tool", "unknown"),
            "result": str(getattr(action, "tool_input", ""))[:200],
        })

    def on_tool_end(self, output: str, **kwargs) -> None:
        if self._actions:
            self._actions[-1]["result"] = str(output)[:200]

    def on_agent_finish(self, finish: Any, **kwargs) -> None:
        output = getattr(finish, "return_values", {}).get("output", "") or str(finish)
        self._messages.append({"role": "assistant", "content": output})
        self._fire_capture(output=output, success=True)

    def on_chain_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs) -> None:
        self._fire_capture(output=str(error), success=False)

    # LangChain v0.2+ uses these names
    on_chain_end = on_agent_finish

    # ── Helpers ─────────────────────────────────────────────────────────────

    def add_message(self, role: str, content: str) -> None:
        """Manually add a message (e.g. intermediate assistant turns)."""
        self._messages.append({"role": role, "content": content})

    def add_diff(self, diff: str) -> None:
        self._diffs.append(diff)

    def set_test_output(self, output: str) -> None:
        self._test_output = output

    def _fire_capture(self, output: str, success: bool | None) -> None:
        try:
            self.mnemo.capture(
                agent_id=self.agent_id,
                task=self._task,
                actions=self._actions,
                output=output,
                success=success,
                time_taken=int((time.time() - self._start) * 1000),
                context=self.context,
                conversation=self._messages,
                code_diffs=self._diffs,
                test_output=self._test_output,
            )
        except Exception:
            pass  # Never crash the agent run due to capture failure
        finally:
            self._diffs = []
            self._test_output = None


class MnemoRecallTool:
    """
    A LangChain-compatible Tool that gives agents the ability to
    explicitly recall lessons mid-task.

    Usage:
        from langchain.tools import Tool
        recall_tool = MnemoRecallTool(mnemo_api_key="...", agent_id="my-agent")
        tools = [recall_tool.as_langchain_tool(), ...]
    """

    def __init__(self, mnemo_api_key: str, agent_id: str, context: dict | None = None):
        self.mnemo = Mnemo(api_key=mnemo_api_key)
        self.agent_id = agent_id
        self.context = context or {}

    def recall(self, task: str) -> str:
        """Called by the agent — returns formatted lessons as text."""
        try:
            return self.mnemo.recall(
                agent_id=self.agent_id,
                task=task,
                as_prompt=True,
                context=self.context,
            ) or "No relevant lessons found."
        except Exception as e:
            return f"Recall unavailable: {e}"

    def as_langchain_tool(self) -> Any:
        """Returns a LangChain Tool object."""
        try:
            from langchain.tools import Tool
            return Tool(
                name="mnemonic_recall",
                func=self.recall,
                description=(
                    "Recall past lessons and fixes relevant to your current task. "
                    "Input: describe the problem you're solving. "
                    "Output: root causes, fix steps, and validation procedures."
                ),
            )
        except ImportError:
            raise ImportError("langchain is required: pip install langchain")
