"""Deterministic, evidence-first highlight candidate construction."""

from dataclasses import dataclass
from typing import Sequence


EVENT_WEIGHTS = {
    "multi_kill": 10.0,
    "kill": 5.0,
    "low_health_turnaround": 8.0,
    "combo": 6.0,
    "audio_peak": 2.5,
    "visual_intensity": 2.0,
}


@dataclass(frozen=True)
class DetectedEvent:
    second: int
    kind: str
    confidence: float


@dataclass(frozen=True)
class HighlightCandidate:
    start_second: int
    end_second: int
    score: float
    evidence: list[DetectedEvent]


def build_candidates(
    events: Sequence[DetectedEvent], window_seconds: int = 12, context_seconds: int = 4
) -> list[HighlightCandidate]:
    """Group nearby detected events into reviewable clips without hiding evidence."""
    if not events:
        return []

    groups: list[list[DetectedEvent]] = []
    for event in sorted(events, key=lambda item: item.second):
        if groups and event.second - groups[-1][-1].second <= window_seconds:
            groups[-1].append(event)
        else:
            groups.append([event])

    candidates = []
    for group in groups:
        score = sum(EVENT_WEIGHTS.get(event.kind, 1.0) * event.confidence for event in group)
        candidates.append(
            HighlightCandidate(
                start_second=max(0, group[0].second - context_seconds),
                end_second=group[-1].second + context_seconds,
                score=round(score, 2),
                evidence=group,
            )
        )
    return candidates
