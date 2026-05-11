"""Pydantic models used by the Mnemo SDK."""
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
