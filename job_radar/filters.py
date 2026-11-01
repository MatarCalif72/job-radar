"""Decide which jobs are relevant, and how relevant."""
from __future__ import annotations

import re

from .sources import Job


def _compile(words: list[str]):
    if not words:
        return None
    parts = [r"(?<![a-z0-9])" + re.escape(w.lower()) + r"(?![a-z0-9])" for w in words]
    return re.compile("|".join(parts))


def _only_israel(loc: str) -> bool:
    """True for "Israel", "Israel (Remote)", "Israel - Hybrid"; False when a city is named."""
    words = set(re.findall(r"[a-z]+", loc))
    return "israel" in words and words <= {"israel", "remote", "hybrid"}


class Matcher:
    def __init__(self, search: dict):
        self.titles = _compile(search.get("titles", []))
        self.exclude = _compile(search.get("exclude_titles", []))
        self.boost = _compile(search.get("boost_titles", []))
        self.locations = [x.lower() for x in search.get("locations", [])]
        # "israel" next to city names means "jobs listed only as Israel", not "anywhere in Israel"
        self.israel_only = "israel" in self.locations and any(x not in ("israel", "remote") for x in self.locations)
        if self.israel_only:
            self.locations.remove("israel")
        self.allow_unknown_location = bool(search.get("include_unknown_location", False))

    def score(self, job: Job) -> int | None:
        """Return a score (higher = better) or None if the job doesn't match."""
        title = job.title.lower()

        if self.exclude and self.exclude.search(title):
            return None

        hits = {m.group(0) for m in self.titles.finditer(title)} if self.titles else set()
        if self.titles and not hits:
            return None

        if self.locations:
            loc = job.location.lower().strip()
            if not loc:
                if not self.allow_unknown_location:
                    return None
            elif not any(x in loc for x in self.locations) and not (self.israel_only and _only_israel(loc)):
                return None

        score = len(hits)
        if self.boost and self.boost.search(title):
            score += 3
        return score
