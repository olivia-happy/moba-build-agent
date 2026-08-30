from app.review_stats import calculate_review_snapshot


def test_review_snapshot_reports_wilson_interval_and_segment_gap():
    reviews = [
        {"voted_up": True, "playtime_forever": 180},
        {"voted_up": True, "playtime_forever": 240},
        {"voted_up": False, "playtime_forever": 300},
        {"voted_up": False, "playtime_forever": 10},
    ]

    snapshot = calculate_review_snapshot(reviews)

    assert snapshot.sample_size == 4
    assert snapshot.recommendation_rate == 0.5
    assert snapshot.interval_low < 0.5 < snapshot.interval_high
    assert snapshot.early_player_rate == 0.0
    assert snapshot.experienced_player_rate == 2 / 3
