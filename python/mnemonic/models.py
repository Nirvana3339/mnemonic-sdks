"""Pydantic models used by the Mnemonic SDK."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Action(BaseModel):
    type: str
    target: str | None = None
    result: str | None = None


class CaptureResponse(BaseModel):
    event_id: str
    status: str
    reflection_queued: bool
    message: str


class LessonHit(BaseModel):
    id: str
    content: str
    lesson_type: str | None = None
    confidence: float
    similarity: float
    context_similarity: float = 0.0
    final_score: float = 0.0
    quality_score: float | None = None
    usage_count: int | None = None
    source: str | None = None
    is_stale: bool = False
    is_deprecated: bool = False
    # Structured fields
    domain: str | None = None
    subdomain: str | None = None
    problem_type: str | None = None
    problem_signature: str | None = None
    root_cause: str | None = None
    solution_steps: list | None = None
    validation_steps: list | None = None
    failure_signals: list | None = None


class ProcedureHit(BaseModel):
    id: str
    name: str
    description: str | None = None
    steps: list = Field(default_factory=list)
    confidence: float
    success_count: int
    failure_count: int
    similarity: float


class RecallResponse(BaseModel):
    lessons: list[LessonHit] = Field(default_factory=list)
    procedures: list[ProcedureHit] = Field(default_factory=list)
    context_prompt: str | None = None
    warnings: list[str] = Field(default_factory=list)
