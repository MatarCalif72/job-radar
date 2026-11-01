"""Build one Telegram message per job and send it."""
from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request

from . import insights
from .sources import Job


def format_job_message(job: Job, skills=()) -> str:
    """One job -> one Telegram message (HTML)."""
    esc = html.escape
    meta = f"🏢 {esc(job.company)}"
    if job.location:
        meta += f"  ·  📍 {esc(job.location)}"

    parts = [f"🆕 <b>{esc(job.title)}</b>", meta]

    summ = insights.summary(job.description)
    parts.append(f"\n📝 {esc(summ)}" if summ else "\n📝 No description available - open the link.")

    know = insights.good_to_know(job, skills)
    if know:
        parts.append("\n💡 <b>Good to know</b>\n" + "\n".join(f"• {esc(k)}" for k in know))

    parts.append(f'\n🔗 <a href="{esc(job.url, quote=True)}">Open the job</a>')
    return "\n".join(parts)


def to_plain(message: str) -> str:
    """HTML message -> readable console text (keeps the link)."""
    message = re.sub(r'<a href="([^"]*)">(.*?)</a>', r"\2: \1", message)
    return html.unescape(re.sub(r"<[^>]+>", "", message))


def build_payload(chat_id: str, text: str, button_url: str | None = None) -> dict:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }
    if button_url:
        payload["reply_markup"] = json.dumps(
            {"inline_keyboard": [[{"text": "⚙️ Redefine jobs", "url": button_url}]]}
        )
    return payload


def send_telegram(token: str, chat_id: str, text: str, button_url: str | None = None) -> None:
    data = urllib.parse.urlencode(build_payload(chat_id, text, button_url)).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.load(resp)
    if not body.get("ok"):
        raise RuntimeError(f"Telegram error: {body}")
