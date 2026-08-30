from fastapi.testclient import TestClient

from app.main import app
from app.video_workflow import DetectedEvent, build_candidates


def test_demo_workflow_module_still_builds_reviewable_evidence_timeline():
    events = [
        DetectedEvent(second=42, kind="multi_kill", confidence=0.94),
        DetectedEvent(second=49, kind="audio_peak", confidence=0.61),
        DetectedEvent(second=133, kind="low_health_turnaround", confidence=0.72),
    ]

    candidates = build_candidates(events)

    assert len(candidates) == 2
    assert candidates[0].evidence[0].kind == "multi_kill"
    assert candidates[0].start_second == 38
    assert candidates[0].end_second == 53


def test_health_reports_offline_ai_mode():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "ai_mode": "offline"}
