from dataclasses import dataclass
from typing import Mapping


DEFAULT_WEIGHTS = {
    "relevance": 0.40,
    "momentum": 0.25,
    "evidence_quality": 0.20,
    "novelty": 0.15,
}


@dataclass(frozen=True)
class ScoreResult:
    score: float
    confidence: float
    contributions: dict[str, float]
    missing_metrics: list[str]


def score_signal(
    metrics: Mapping[str, float | None], weights: Mapping[str, float]
) -> ScoreResult:
    """Calculate a transparent 0-100 score without silently imputing missing values."""
    missing = [name for name in weights if metrics.get(name) is None]
    contributions = {
        name: round(float(metrics[name]) * weight * 100, 2)
        for name, weight in weights.items()
        if metrics.get(name) is not None
    }
    observed = [float(value) for value in metrics.values() if value is not None]
    coverage = len(observed) / len(weights) if weights else 0.0
    return ScoreResult(
        score=round(sum(contributions.values()), 2),
        confidence=round((sum(observed) / len(observed)) * coverage, 2) if observed else 0.0,
        contributions=contributions,
        missing_metrics=missing,
    )
