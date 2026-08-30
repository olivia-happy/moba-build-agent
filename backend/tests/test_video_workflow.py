from app.video_workflow import DetectedEvent, build_candidates


def test_build_candidates_merges_nearby_events_and_keeps_evidence():
    events = [
        DetectedEvent(second=12, kind="multi_kill", confidence=0.9),
        DetectedEvent(second=18, kind="audio_peak", confidence=0.5),
    ]

    candidates = build_candidates(events)

    assert len(candidates) == 1
    assert candidates[0].start_second == 8
    assert candidates[0].end_second == 22
    assert candidates[0].score == 10.25
    assert candidates[0].evidence[0].kind == "multi_kill"
