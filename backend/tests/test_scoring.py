from app.scoring import DEFAULT_WEIGHTS, score_signal


def test_score_signal_returns_bounded_score_and_contributions():
    result = score_signal(
        {"relevance": 0.9, "momentum": 0.7, "evidence_quality": 0.8, "novelty": 0.6},
        DEFAULT_WEIGHTS,
    )

    assert result.score == 78.5
    assert result.confidence == 0.75
    assert result.contributions["relevance"] == 36.0


def test_score_signal_penalizes_missing_indicators():
    result = score_signal(
        {"relevance": 1.0, "momentum": None, "evidence_quality": 1.0, "novelty": 1.0},
        DEFAULT_WEIGHTS,
    )

    assert result.missing_metrics == ["momentum"]
    assert result.score < 100
    assert result.confidence < 1
