"""Find which job board (Greenhouse, Lever, Ashby) each company uses, from just its name.

For every name it tries likely board names ("check point" -> checkpoint, check-point, ...)
on each service. A board counts only if it lists at least one job in Israel, which also
protects against picking up a different company that happens to share the name.
"""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from . import sources

ATS_ORDER = ["greenhouse", "lever", "ashby", "greenhouse-eu"]

ISRAEL_WORDS = [
    "israel", "tel aviv", "tel-aviv", "ramat gan", "herzliya", "petah tikva", "petach tikva",
    "haifa", "jerusalem", "beer sheva", "be'er sheva", "netanya", "rehovot", "raanana",
    "ra'anana", "kfar saba", "holon", "givatayim", "rishon", "yokneam", "or yehuda",
    "bnei brak", "hod hasharon", "caesarea",
]

TLD_WORDS = {"com", "io", "ai", "co", "app", "net", "org"}
SUFFIXES = ["inc", "hq", "io", "is", "israel"]


def _unique(items):
    seen, out = set(), []
    for x in items:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def read_names(path) -> list[str]:
    p = Path(path)
    if not p.exists():
        return []
    names, seen = [], set()
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line and line.lower() not in seen:
            seen.add(line.lower())
            names.append(line)
    return names


def slug_variants(name: str) -> tuple[list[str], list[str]]:
    """(likely board names, less likely ones). The second group is tried only if the first finds nothing."""
    tokens = re.findall(r"[a-z0-9]+", name.lower())
    while len(tokens) > 1 and tokens[-1] in TLD_WORDS:
        tokens.pop()
    if not tokens:
        return [], []
    joined, hyphen, first = "".join(tokens), "-".join(tokens), tokens[0]
    round1 = _unique([joined, hyphen, first])
    round2 = [s for s in _unique([joined + x for x in SUFFIXES] + [first + "inc"]) if s not in round1]
    return round1, round2


def probe(name, ats, slug, fetcher, words):
    """Return a result dict if this board exists and has jobs, else None."""
    try:
        jobs = fetcher({"name": name, "ats": ats, "slug": slug})
    except Exception:
        return None
    if not jobs:
        return None
    israel = sum(1 for j in jobs if any(w in (j.location or "").lower() for w in words))
    return {"name": name, "ats": ats, "slug": slug, "jobs": len(jobs), "israel_jobs": israel}


def discover(names, fetcher=None, israel_words=None, min_israel=1, workers=12, on_result=None):
    """Return (boards found, names with no board found)."""
    fetcher = fetcher or (lambda c: sources.fetch(c, light=True))
    words = [w.lower() for w in (israel_words or ISRAEL_WORDS)]

    def one(name):
        for group in slug_variants(name):
            hits, seen = [], set()
            for slug in group:
                for ats in ATS_ORDER:
                    r = probe(name, ats, slug, fetcher, words)
                    if r and r["israel_jobs"] >= min_israel and (ats, slug) not in seen:
                        seen.add((ats, slug))
                        hits.append(r)
            if hits:
                return hits
        return []

    found, missing = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for name, hits in zip(names, pool.map(one, names)):
            if hits:
                found.extend(hits)
            else:
                missing.append(name)
            if on_result:
                on_result(name, hits)
    return found, missing


# ---- saved results (companies_found.json) ---------------------------------

def load_found(path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        items = data.get("companies", []) if isinstance(data, dict) else []
    except Exception as exc:
        print(f"warning: ignoring {p}: {exc}", file=sys.stderr)
        return []
    return [c for c in items if isinstance(c, dict) and c.get("name") and c.get("ats") and c.get("slug")]


def save_found(path, companies: list[dict], today: date | None = None) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated": (today or date.today()).isoformat(),
        "companies": sorted(companies, key=lambda c: (c["name"].lower(), c["ats"], c["slug"])),
    }
    p.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def update_found(existing: list[dict], new_hits: list[dict]) -> list[dict]:
    """New results replace old ones for the same company; companies not found this time are kept."""
    renewed = {h["name"].lower() for h in new_hits}
    return [e for e in existing if e["name"].lower() not in renewed] + list(new_hits)


def merge_companies(config_companies: list[dict], found: list[dict]) -> list[dict]:
    """config.toml entries first, then discovered ones, without duplicates."""
    out, seen = [], set()
    for c in list(config_companies) + list(found):
        key = (str(c["ats"]).lower(), str(c["slug"]).lower())
        if key not in seen:
            seen.add(key)
            out.append({"name": c["name"], "ats": c["ats"], "slug": c["slug"]})
    return out
