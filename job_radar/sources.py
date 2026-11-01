"""Fetch open jobs (with descriptions) from public ATS job-board APIs."""
from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

USER_AGENT = "job-radar/1.0 (personal job alert bot)"

URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
    # Greenhouse boards hosted in the EU (best effort - not confirmed from here)
    "greenhouse-eu": "https://boards-api.eu.greenhouse.io/v1/boards/{slug}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
}

# Same boards without the long descriptions: faster, used when only checking a board exists
LIGHT_URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "greenhouse-eu": "https://boards-api.eu.greenhouse.io/v1/boards/{slug}/jobs",
}


@dataclass(frozen=True)
class Job:
    source: str
    company: str
    id: str
    title: str
    location: str
    url: str
    description: str = field(default="", compare=False, repr=False)  # plain text

    @property
    def key(self) -> str:
        return f"{self.source}:{self.company}:{self.id}"


def html_to_text(s: str | None) -> str:
    """Turn (possibly escaped) HTML into readable plain text with line breaks."""
    if not s:
        return ""
    s = html.unescape(s)  # Greenhouse sends escaped HTML
    s = re.sub(r"(?is)<\s*(script|style)[^>]*>.*?<\s*/\s*\1\s*>", " ", s)
    s = re.sub(r"(?i)<\s*li[^>]*>", "\n- ", s)
    s = re.sub(r"(?i)<\s*br\s*/?\s*>|<\s*/\s*(p|div|h[1-6]|ul|ol|li)\s*>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v ]+", " ", s)
    s = "\n".join(line.strip() for line in s.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def parse_greenhouse(company: str, data: dict) -> list[Job]:
    return [
        Job(
            "greenhouse",
            company,
            str(j["id"]),
            j.get("title", ""),
            (j.get("location") or {}).get("name", "") or "",
            j.get("absolute_url", ""),
            html_to_text(j.get("content")),
        )
        for j in data.get("jobs", [])
    ]


def _lever_text(j: dict) -> str:
    parts = [j.get("descriptionPlain") or html_to_text(j.get("description"))]
    for block in j.get("lists") or []:
        parts.append(f"{block.get('text', '')}\n{html_to_text(block.get('content'))}")
    parts.append(j.get("additionalPlain") or html_to_text(j.get("additional")))
    return "\n\n".join(p for p in parts if p and p.strip())


def parse_lever(company: str, data: list) -> list[Job]:
    return [
        Job(
            "lever",
            company,
            str(j["id"]),
            j.get("text", ""),
            (j.get("categories") or {}).get("location") or "",
            j.get("hostedUrl", ""),
            _lever_text(j),
        )
        for j in data
    ]


def parse_ashby(company: str, data: dict) -> list[Job]:
    jobs = []
    for j in data.get("jobs", []):
        location = j.get("location") or ""
        if j.get("isRemote") and "remote" not in location.lower():
            location = f"{location} (Remote)".strip()
        text = j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml"))
        jobs.append(
            Job("ashby", company, str(j["id"]), j.get("title", ""), location, j.get("jobUrl", ""), text)
        )
    return jobs


PARSERS = {
    "greenhouse": parse_greenhouse,
    "greenhouse-eu": parse_greenhouse,
    "lever": parse_lever,
    "ashby": parse_ashby,
}


def get_json(url: str, timeout: int = 30, retries: int = 2):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code < 500:  # 404 etc.: trying again won't help
                raise
            last = exc
            if attempt + 1 < retries:
                time.sleep(2)
        except Exception as exc:  # network / JSON errors
            last = exc
            if attempt + 1 < retries:
                time.sleep(2)
    raise last


def fetch(company: dict, light: bool = False) -> list[Job]:
    """company = {"name": ..., "ats": "greenhouse|greenhouse-eu|lever|ashby", "slug": ...}"""
    ats = company["ats"].lower()
    if ats not in URLS:
        raise ValueError(f"unknown ats '{ats}' (use: {', '.join(URLS)})")
    url = (LIGHT_URLS.get(ats) if light else None) or URLS[ats]
    data = get_json(url.format(slug=company["slug"]))
    return PARSERS[ats](company["name"], data)
