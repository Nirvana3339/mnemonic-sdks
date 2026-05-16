"""
Mnemonic post-install setup.

Runs automatically on first Mnemo() instantiation.
Also available as a CLI: mnemo-setup

What it does:
  1. Installs the Claude Code Stop hook (~/.claude/settings.json)
  2. Creates ~/.mnemo/.installed flag so it never runs twice
  3. Prints one-time setup instructions
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

FLAG_FILE = pathlib.Path.home() / ".mnemo" / ".installed"
CLAUDE_SETTINGS = pathlib.Path.home() / ".claude" / "settings.json"


def _install_claudecode_hook() -> bool:
    """Install the Stop hook into ~/.claude/settings.json. Returns True if installed."""
    try:
        CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        settings = {}
        if CLAUDE_SETTINGS.exists():
            try:
                settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
            except Exception:
                settings = {}

        hook_command = f"{sys.executable} -m mnemo.integrations.claudecode.hook"
        hooks = settings.setdefault("hooks", {})
        stop_hooks = hooks.setdefault("Stop", [])

        # Already installed?
        for hook in stop_hooks:
            if isinstance(hook, dict):
                for h in hook.get("hooks", []):
                    if hook_command in str(h.get("command", "")):
                        return False  # Already there

        stop_hooks.append({
            "matcher": "",
            "hooks": [{"type": "command", "command": hook_command}],
        })

        CLAUDE_SETTINGS.write_text(
            json.dumps(settings, indent=2), encoding="utf-8"
        )
        return True
    except Exception:
        return False


def _mark_installed() -> None:
    FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)
    FLAG_FILE.write_text("1", encoding="utf-8")


def is_installed() -> bool:
    return FLAG_FILE.exists()


def auto_setup(silent: bool = True) -> None:
    """
    Called automatically on first Mnemo() instantiation.
    Installs Claude Code hook if not already set up.
    """
    if is_installed():
        return

    hook_installed = _install_claudecode_hook()
    _mark_installed()

    if not silent and hook_installed:
        print(
            "\n[Mnemonic] Claude Code auto-capture hook installed.\n"
            "Set MNEMO_API_KEY in your environment to enable lesson capture.\n"
            "Every Claude Code session will now be captured automatically.\n"
        )


def run() -> None:
    """Entry point for `mnemo-setup` CLI command."""
    print("Mnemonic Setup")
    print("=" * 40)

    # 1. Claude Code hook
    hook_installed = _install_claudecode_hook()
    if hook_installed:
        print(f"[OK] Claude Code hook installed in {CLAUDE_SETTINGS}")
    else:
        print(f"[--] Claude Code hook already present in {CLAUDE_SETTINGS}")

    _mark_installed()

    # 2. Environment check
    api_key = os.environ.get("MNEMO_API_KEY", "")
    if api_key:
        print(f"[OK] MNEMO_API_KEY is set")
    else:
        print(f"[!!] MNEMO_API_KEY not set — add to your shell profile:")
        print(f"     export MNEMO_API_KEY=mnemo_sk_...")

    agent_id = os.environ.get("MNEMO_AGENT_ID", "")
    if agent_id:
        print(f"[OK] MNEMO_AGENT_ID = {agent_id}")
    else:
        print(f"[  ] MNEMO_AGENT_ID not set (default: claude-code-agent)")

    print("\nSetup complete. Every Claude Code session will now auto-capture lessons.")
