"""Fetch open jobs from public ATS job-board APIs (Greenhouse, Lever, Ashby)."""
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass

USER_AGENT = "job-radar/1.0 (personal job alert bot)"

URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
}


@dataclass(frozen=True)
class Job:
    source: str
    company: str
    id: str
    title: str
    location: str
    url: str

    @property
    def key(self) -> str:
        return f"{self.source}:{self.company}:{self.id}"


def parse_greenhouse(company: str, data: dict) -> list[Job]:
    return [
        Job(
            "greenhouse",
            company,
            str(j["id"]),
            j.get("title", ""),
            (j.get("location") or {}).get("name", "") or "",
            j.get("absolute_url", ""),
        )
        for j in data.get("jobs", [])
    ]


def parse_lever(company: str, data: list) -> list[Job]:
    return [
        Job(
            "lever",
            company,
            str(j["id"]),
            j.get("text", ""),
            (j.get("categories") or {}).get("location") or "",
            j.get("hostedUrl", ""),
        )
        for j in data
    ]


def parse_ashby(company: str, data: dict) -> list[Job]:
    jobs = []
    for j in data.get("jobs", []):
        location = j.get("location") or ""
        if j.get("isRemote") and "remote" not in location.lower():
            location = f"{location} (Remote)".strip()
        jobs.append(
            Job("ashby", company, str(j["id"]), j.get("title", ""), location, j.get("jobUrl", ""))
        )
    return jobs


PARSERS = {
    "greenhouse": parse_greenhouse,
    "lever": parse_lever,
    "ashby": parse_ashby,
}


def get_json(url: str, timeout: int = 20, retries: int = 2):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except Exception as exc:  # network / HTTP / JSON errors
            last = exc
            if attempt + 1 < retries:
                time.sleep(2)
    raise last


def fetch(company: dict) -> list[Job]:
    """company = {"name": ..., "ats": "greenhouse|lever|ashby", "slug": ...}"""
    ats = company["ats"].lower()
    if ats not in URLS:
        raise ValueError(f"unknown ats '{ats}' (use: {', '.join(URLS)})")
    data = get_json(URLS[ats].format(slug=company["slug"]))
    return PARSERS[ats](company["name"], data)
