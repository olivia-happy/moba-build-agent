from dataclasses import dataclass
from math import sqrt
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ReviewSnapshot:
    sample_size: int
    recommendation_rate: float
    interval_low: float
    interval_high: float
    early_player_rate: float | None
    experienced_player_rate: float | None


def _rate(rows: Sequence[Mapping[str, object]]) -> float | None:
    if not rows:
        return None
    return sum(bool(row["voted_up"]) for row in rows) / len(rows)


def _wilson_interval(successes: int, sample_size: int, z: float = 1.96) -> tuple[float, float]:
    if sample_size == 0:
        return 0.0, 0.0
    proportion = successes / sample_size
    denominator = 1 + z**2 / sample_size
    centre = (proportion + z**2 / (2 * sample_size)) / denominator
    margin = z * sqrt((proportion * (1 - proportion) + z**2 / (4 * sample_size)) / sample_size) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def calculate_review_snapshot(reviews: Sequence[Mapping[str, object]]) -> ReviewSnapshot:
    sample_size = len(reviews)
    positives = sum(bool(review["voted_up"]) for review in reviews)
    interval_low, interval_high = _wilson_interval(positives, sample_size)
    early = [review for review in reviews if int(review.get("playtime_forever", 0)) < 120]
    experienced = [review for review in reviews if int(review.get("playtime_forever", 0)) >= 120]
    return ReviewSnapshot(
        sample_size=sample_size,
        recommendation_rate=positives / sample_size if sample_size else 0.0,
        interval_low=interval_low,
        interval_high=interval_high,
        early_player_rate=_rate(early),
        experienced_player_rate=_rate(experienced),
    )
