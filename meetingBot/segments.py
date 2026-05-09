from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TranscriptSegment:
    started_at: str
    ended_at: str
    duration_seconds: float
    text: str
    language: str | None = None
    meeting_id: str | None = None
    task: str = "transcribe"

