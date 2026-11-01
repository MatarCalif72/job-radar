"""Format the digest and send it to Telegram."""
from __future__ import annotations

import html
import json
import urllib.parse
import urllib.request

from .sources import Job

MAX_LEN = 3800  # Telegram limit is 4096


def _line(job: Job) -> str:
    loc = f" ({html.escape(job.location)})" if job.location else ""
    return (
        f'• <a href="{html.escape(job.url, quote=True)}">{html.escape(job.title)}</a>'
        f" — {html.escape(job.company)}{loc}"
    )


def format_digest(jobs: list[Job]) -> list[str]:
    """Return one or more Telegram messages (HTML) listing the jobs."""
    if not jobs:
        return []
    header = f"🔎 <b>{len(jobs)} new job{'s' if len(jobs) != 1 else ''}</b>\n"
    messages, current = [], header
    for job in jobs:
        line = _line(job) + "\n"
        if len(current) + len(line) > MAX_LEN:
            messages.append(current.rstrip())
            current = ""
        current += line
    if current.strip():
        messages.append(current.rstrip())
    return messages


def format_plain(jobs: list[Job]) -> str:
    return "\n".join(f"- {j.title} | {j.company} | {j.location or '?'} | {j.url}" for j in jobs)


def send_telegram(token: str, chat_id: str, text: str) -> None:
    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
    ).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.load(resp)
    if not body.get("ok"):
        raise RuntimeError(f"Telegram error: {body}")
