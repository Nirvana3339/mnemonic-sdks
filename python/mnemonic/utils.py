"""Prompt-formatting helpers used by integration wrappers."""
from __future__ import annotations


def format_lessons_block(lessons: list[dict]) -> str:
    if not lessons:
        return ""
    return "\n".join(f"• {l['content']}" for l in lessons)
