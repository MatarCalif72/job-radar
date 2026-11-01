"""Remember which jobs were already sent, in a small JSON file."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path


def load(path) -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8")).get("seen", {})


def save(path, seen: dict[str, str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"seen": dict(sorted(seen.items()))}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def prune(seen: dict[str, str], current_keys: set[str], today: date, days: int = 60):
    """Drop jobs that are no longer listed and were first seen over `days` ago."""
    return {
        k: v
        for k, v in seen.items()
        if k in current_keys or (today - date.fromisoformat(v)).days <= days
    }
