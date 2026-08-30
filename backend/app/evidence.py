from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


@dataclass(frozen=True)
class CanonicalEvidence:
    title: str
    source_url: str
    source_name: str
    published_at: datetime | None
    retrieved_at: datetime
    summary: str
    quality_flags: list[str]


def _strip_tracking(url: str) -> str:
    parts = urlsplit(url)
    filtered = [(key, value) for key, value in parse_qsl(parts.query) if not key.lower().startswith("utm_")]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(filtered), ""))


def evidence_fingerprint(title: str, source_url: str, published_at: datetime | None) -> str:
    value = "|".join((title.strip().lower(), _strip_tracking(source_url), published_at.isoformat() if published_at else ""))
    return sha256(value.encode("utf-8")).hexdigest()


def canonicalize_item(
    *, title: str, url: str, source_name: str, published_at: datetime | None, summary: str
) -> CanonicalEvidence:
    flags: list[str] = []
    if published_at is None:
        flags.append("missing_published_at")
    if not summary.strip():
        flags.append("missing_summary")
    return CanonicalEvidence(
        title=title.strip(),
        source_url=_strip_tracking(url),
        source_name=source_name.strip(),
        published_at=published_at,
        retrieved_at=datetime.now(timezone.utc),
        summary=summary.strip(),
        quality_flags=flags,
    )
