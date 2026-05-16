"""
Claude Code auto-capture hook.

Reads the Stop event from Claude Code stdin and fires mnemonic_capture
automatically — no manual calls needed in any Claude Code session.

Setup (one time):
    python -m mnemo.integrations.claudecode.hook install

This adds a Stop hook to ~/.claude/settings.json that fires this script
after every Claude Code session ends.

Manual test:
    echo '{"session_id":"test","transcript":[]}' | python -m mnemo.integrations.claudecode.hook
"""
from __future__ import annotations

import json
import os
import sys


MNEMO_API_KEY = os.environ.get("MNEMO_API_KEY", "")
MNEMO_BASE_URL = os.environ.get("MNEMO_BASE_URL", "https://api.mnemo.dev/v1")
MNEMO_AGENT_ID = os.environ.get("MNEMO_AGENT_ID", "claude-code-agent")
MNEMO_CONTEXT = json.loads(os.environ.get("MNEMO_CONTEXT", "{}"))


def _extract_conversation(transcript: list[dict]) -> list[dict]:
    """Convert Claude Code transcript format to mnemonic conversation format."""
    messages = []
    for turn in transcript:
        role = turn.get("role", "")
        if role not in ("user", "assistant"):
            continue
        # Claude Code transcript may have content as string or list of blocks
        content = turn.get("content", "")
        if isinstance(content, list):
            # Extract text from content blocks
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_result":
                        text_parts.append(f"[tool_result: {str(block.get('content', ''))[:200]}]")
                    elif block.get("type") == "tool_use":
                        text_parts.append(f"[tool_use: {block.get('name', '')} {str(block.get('input', ''))[:200]}]")
            content = " ".join(text_parts)
        if content:
            messages.append({"role": role, "content": str(content)[:1000]})
    return messages


def _extract_task(transcript: list[dict], hook_data: dict) -> str:
    """Extract the primary task from the session."""
    # Try session summary first
    if hook_data.get("summary"):
        return hook_data["summary"][:300]
    # Fall back to first user message
    for turn in transcript:
        if turn.get("role") == "user":
            content = turn.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        return block.get("text", "")[:300]
            return str(content)[:300]
    return "Claude Code session"


def _extract_diffs(transcript: list[dict]) -> list[str]:
    """Find code diffs/edits made during the session."""
    diffs = []
    for turn in transcript:
        content = turn.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            # Tool use blocks for Edit/Write tools contain code changes
            if block.get("type") == "tool_use" and block.get("name") in ("Edit", "Write", "str_replace_editor"):
                inp = block.get("input", {})
                if isinstance(inp, dict):
                    diff_hint = (
                        f"File: {inp.get('file_path', inp.get('path', '?'))}\n"
                        f"Old: {str(inp.get('old_string', ''))[:200]}\n"
                        f"New: {str(inp.get('new_string', inp.get('content', ''))[:200])}"
                    )
                    diffs.append(diff_hint)
    return diffs[:5]


def _extract_test_output(transcript: list[dict]) -> str | None:
    """Find test/build output in tool results."""
    test_keywords = ["passed", "failed", "error", "pytest", "jest", "npm test", "cargo test"]
    for turn in reversed(transcript):  # Most recent first
        content = turn.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result":
                result_text = str(block.get("content", "")).lower()
                if any(kw in result_text for kw in test_keywords):
                    return str(block.get("content", ""))[:500]
    return None


def run_hook(hook_data: dict) -> None:
    """Process a Claude Code Stop hook event and fire mnemonic capture."""
    if not MNEMO_API_KEY:
        # Silently skip — hook configured but key not set
        return

    transcript = hook_data.get("transcript", [])
    if not transcript:
        return

    task = _extract_task(transcript, hook_data)
    conversation = _extract_conversation(transcript)
    diffs = _extract_diffs(transcript)
    test_output = _extract_test_output(transcript)

    # Build context from environment hints in the session
    context = dict(MNEMO_CONTEXT)

    try:
        import httpx
        response = httpx.post(
            f"{MNEMO_BASE_URL}/events",
            headers={
                "Authorization": f"Bearer {MNEMO_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "agent_id": MNEMO_AGENT_ID,
                "task": task,
                "output": conversation[-1]["content"] if conversation else "",
                "context": context,
                "conversation": conversation,
                "code_diffs": diffs,
                "test_output": test_output,
            },
            timeout=10,
        )
        response.raise_for_status()
    except Exception:
        pass  # Never crash Claude Code due to capture failure


def install() -> None:
    """Add this hook to ~/.claude/settings.json."""
    import pathlib

    settings_path = pathlib.Path.home() / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except Exception:
            settings = {}

    hook_command = f"{sys.executable} -m mnemo.integrations.claudecode.hook"

    hooks = settings.setdefault("hooks", {})
    stop_hooks = hooks.setdefault("Stop", [])

    # Check if already installed
    for hook in stop_hooks:
        if isinstance(hook, dict) and hook_command in str(hook.get("command", "")):
            print("Mnemonic hook already installed.")
            return

    stop_hooks.append({
        "matcher": "",
        "hooks": [{"type": "command", "command": hook_command}],
    })

    settings_path.write_text(json.dumps(settings, indent=2))
    print(f"Mnemonic hook installed in {settings_path}")
    print(f"Set MNEMO_API_KEY environment variable to enable capture.")
    print(f"Optionally set MNEMO_AGENT_ID (default: claude-code-agent)")
    print(f"Optionally set MNEMO_CONTEXT as JSON (e.g. '{{\"framework\":\"react\"}}')")


def uninstall() -> None:
    """Remove the hook from ~/.claude/settings.json."""
    import pathlib

    settings_path = pathlib.Path.home() / ".claude" / "settings.json"
    if not settings_path.exists():
        print("No settings file found.")
        return

    settings = json.loads(settings_path.read_text())
    hook_command = f"{sys.executable} -m mnemo.integrations.claudecode.hook"

    hooks = settings.get("hooks", {})
    stop_hooks = hooks.get("Stop", [])
    hooks["Stop"] = [
        h for h in stop_hooks
        if not (isinstance(h, dict) and hook_command in str(h.get("command", "")))
    ]

    settings_path.write_text(json.dumps(settings, indent=2))
    print("Mnemonic hook removed.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "install":
            install()
        elif sys.argv[1] == "uninstall":
            uninstall()
        sys.exit(0)

    # Read hook data from stdin (Claude Code passes JSON on stdin)
    try:
        hook_data = json.loads(sys.stdin.read())
        run_hook(hook_data)
    except Exception:
        pass  # Never crash Claude Code
