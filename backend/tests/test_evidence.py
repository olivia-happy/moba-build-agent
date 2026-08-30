from datetime import datetime, timezone

from app.evidence import canonicalize_item, evidence_fingerprint


def test_canonicalize_item_keeps_source_and_detects_missing_timestamp():
    item = canonicalize_item(
        title="Battery storage policy update",
        url="https://example.com/news?utm_source=rss",
        source_name="Public Energy Desk",
        published_at=None,
        summary="A public update.",
    )

    assert item.source_url == "https://example.com/news"
    assert item.quality_flags == ["missing_published_at"]
    assert item.retrieved_at.tzinfo == timezone.utc


def test_evidence_fingerprint_is_stable_for_same_source_item():
    timestamp = datetime(2026, 8, 18, tzinfo=timezone.utc)

    first = evidence_fingerprint("A title", "https://example.com/a", timestamp)
    second = evidence_fingerprint("A title", "https://example.com/a", timestamp)

    assert first == second
