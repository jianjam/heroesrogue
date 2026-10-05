from __future__ import annotations

from pathlib import Path


def icon_file_name(icon_source: str | Path) -> str:
    stem = Path(icon_source).stem.strip().lower().replace("-", "_")
    return f"{stem}.png" if stem else ""
