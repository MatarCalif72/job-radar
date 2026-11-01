"""Turn a long job description into a short summary and a few useful facts.

Plain rules, no AI and no cost: it finds the "what you'll do" part, pulls the
years of experience asked for, and compares the tools mentioned to your skills.
"""
from __future__ import annotations

import re

from .sources import Job

SECTION_HEADS = [
    "about the role", "the role", "your role", "role overview", "job description",
    "what you'll do", "what you will do", "what you'll be doing", "responsibilities",
    "your mission", "the opportunity", "in this role", "position overview",
    "the position", "the job", "key responsibilities",
]

STOP_HEADS = [
    "requirements", "qualifications", "what we're looking for", "what you bring",
    "who you are", "about you", "nice to have", "skills", "benefits", "what we offer",
]

# display name -> regex (matched on lowercase text, with word boundaries)
TECH = {
    "AWS": r"aws|amazon web services",
    "Azure": r"azure",
    "GCP": r"gcp|google cloud",
    "Docker": r"docker",
    "Kubernetes": r"kubernetes|k8s",
    "Terraform": r"terraform",
    "Ansible": r"ansible",
    "Jenkins": r"jenkins",
    "GitHub Actions": r"github actions",
    "GitLab": r"gitlab",
    "CI/CD": r"ci\s*/\s*cd|ci-cd",
    "Linux": r"linux",
    "Bash": r"bash",
    "Python": r"python",
    "Java": r"java",
    "JavaScript": r"javascript",
    "TypeScript": r"typescript",
    "Node.js": r"node\.?js",
    "React": r"react",
    "C#": r"c#",
    ".NET": r"\.net|dotnet",
    "Go": r"golang",
    "SQL": r"sql",
    "PostgreSQL": r"postgres(?:ql)?",
    "MongoDB": r"mongo(?:db)?",
    "Redis": r"redis",
    "Kafka": r"kafka",
    "Prometheus": r"prometheus",
    "Grafana": r"grafana",
    "Datadog": r"datadog",
    "Helm": r"helm",
}
_TECH_RE = {
    name: re.compile(r"(?<![a-z0-9])(?:" + pat + r")(?![a-z0-9])") for name, pat in TECH.items()
}


def summary(text: str, max_chars: int = 320) -> str:
    """A couple of sentences about the role itself (skips company intro when it can)."""
    if not text:
        return ""
    lines = [l.strip() for l in text.split("\n")]
    body = lines
    for i, line in enumerate(lines):
        low = line.lower().replace("’", "'").strip(" :-–*")
        if len(low) < 60 and any(low.startswith(h) for h in SECTION_HEADS):
            body = lines[i + 1 :]
            break

    pieces = []
    for line in body:
        low = line.lower().replace("’", "'").strip(" :-–*")
        if len(low) < 60 and any(low.startswith(h) for h in STOP_HEADS):
            break  # requirements are covered under "Good to know"
        line = line.lstrip("-•* ").rstrip()
        if len(line) < 25:
            continue
        if line[-1] not in ".!?":
            line += "."
        pieces.append(line)
        if len(pieces) >= 6:
            break

    out = ""
    for sentence in re.split(r"(?<=[.!?])\s+", " ".join(pieces)):
        if out and len(out) + len(sentence) + 1 > max_chars:
            break
        out = f"{out} {sentence}".strip()
        if len(out) >= max_chars:
            break
    if len(out) > max_chars:
        out = out[: max_chars - 1].rstrip() + "…"
    return out


def years_required(text: str) -> int | None:
    """Lowest 'N years' figure that is talking about experience."""
    nums = []
    pattern = r"(\d{1,2})\s*\+?\s*(?:(?:-|–|to)\s*\d{1,2}\s*\+?\s*)?years?"
    for m in re.finditer(pattern, text, re.I):
        window = text[max(0, m.start() - 80) : m.end() + 80].lower()
        if "experience" in window and int(m.group(1)) > 0:
            nums.append(int(m.group(1)))
    return min(nums) if nums else None


def tech_found(text: str) -> list[str]:
    low = text.lower()
    return [name for name, rx in _TECH_RE.items() if rx.search(low)]


def work_mode(text: str, location: str = "") -> str | None:
    low = f"{text} {location}".lower()
    modes = []
    if re.search(r"hybrid", low):
        modes.append("Hybrid")
    if re.search(r"on-?site|in-?office|in the office", low):
        modes.append("On-site")
    if re.search(r"remote", low):
        modes.append("Remote mentioned")
    return " / ".join(modes) or None


def good_to_know(job: Job, skills=()) -> list[str]:
    text = job.description or ""
    title = job.title.lower()
    out: list[str] = []

    if re.search(r"(?<![a-z])(junior|jr|entry[- ]level|graduate)(?![a-z])", title):
        out.append("Junior-level role")
    if re.search(r"(?<![a-z])(student|intern|internship)(?![a-z])", title):
        out.append("Student / intern position")

    if text:
        n = years_required(text)
        out.append(f"Asks for {n}+ years of experience" if n else "No years of experience mentioned")

        mine = {s.lower() for s in skills}
        tech = tech_found(text)
        have = [t for t in tech if t.lower() in mine]
        other = [t for t in tech if t.lower() not in mine][:6]
        if have:
            out.append("Matches your skills: " + ", ".join(have))
        if other:
            out.append("Also asks for: " + ", ".join(other))

        mode = work_mode(text, job.location)
        if mode:
            out.append(f"Work mode: {mode}")
        if re.search(r"hebrew", text, re.I):
            out.append("Hebrew is mentioned")
        if re.search(r"security clearance|clearance", text, re.I):
            out.append("Mentions security clearance")
    return out
