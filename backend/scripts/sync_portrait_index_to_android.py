"""Copy the verified portrait index into the Android app's assets.

Usage (repo root):
    .\\.venv\\Scripts\\python.exe backend/scripts/sync_portrait_index_to_android.py

The script refuses to copy a corrupted or stale index (schema mismatch or
content hash mismatch) so the app bundle can never contain a broken file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.portrait_index import load_index  # noqa: E402

DEFAULT_SOURCE = ROOT / "data" / "portrait_index.json"
DEFAULT_DESTINATION = (
    ROOT / "android-app" / "app" / "src" / "main" / "assets" / "portrait_index.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    args = parser.parse_args(argv)

    source = args.source
    destination = args.destination
    index = load_index(source)  # raises on schema/hash mismatch
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    print(
        f"synced {source.name} -> {destination.relative_to(ROOT)} "
        f"heroes={index.hero_count} hash={index.content_hash[:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
