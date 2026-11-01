"""Settings saved by the "Redefine jobs" page (my_search.json) override config.toml."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _strings(value):
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    return None


def apply_overrides(cfg: dict, path) -> tuple[dict, bool]:
    """Return (new config, whether the file was used). Bad files are ignored with a warning."""
    p = Path(path)
    if not p.exists():
        return cfg, False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object")
    except Exception as exc:
        print(f"warning: ignoring {p}: {exc}", file=sys.stderr)
        return cfg, False

    search = dict(cfg.get("search", {}))
    titles = _strings(data.get("titles"))
    if titles:  # an empty title list would match every job, so keep the old one
        search["titles"] = titles
    for key in ("exclude_titles", "boost_titles", "locations"):
        values = _strings(data.get(key))
        if values is not None:  # empty is valid: "any level" / "anywhere"
            search[key] = values
    if isinstance(data.get("include_unknown_location"), bool):
        search["include_unknown_location"] = data["include_unknown_location"]

    out = dict(cfg)
    out["search"] = search
    skills = _strings(data.get("skills"))
    if skills is not None:
        out["profile"] = {**cfg.get("profile", {}), "skills": skills}
    return out, True


def pages_url(repo: str | None) -> str | None:
    """GitHub Pages address of the Redefine page, derived from 'owner/repo'."""
    if not repo or "/" not in repo:
        return None
    owner, name = repo.split("/", 1)
    return f"https://{owner.lower()}.github.io/{name}/"
