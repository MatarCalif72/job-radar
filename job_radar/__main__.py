"""Run: python -m job_radar [--dry-run] [--check]"""
from __future__ import annotations

import argparse
import os
import sys
import tomllib
from datetime import date

from . import filters, notify, sources, store


def load_config(path: str) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def collect(companies: list[dict]):
    jobs, errors = [], []
    for c in companies:
        try:
            jobs.extend(sources.fetch(c))
        except Exception as exc:
            errors.append(f"{c.get('name', '?')}: {exc}")
    return jobs, errors


def check(companies: list[dict]) -> int:
    """Verify each company's board name works."""
    bad = 0
    for c in companies:
        try:
            n = len(sources.fetch(c))
            print(f"OK    {c['name']:<20} {n} open jobs")
        except Exception as exc:
            bad += 1
            print(f"FAIL  {c['name']:<20} {exc}")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="job_radar")
    ap.add_argument("--config", default="config.toml")
    ap.add_argument("--state", default="data/seen.json")
    ap.add_argument("--dry-run", action="store_true", help="print results, don't send or save")
    ap.add_argument("--check", action="store_true", help="test every company in the config")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    companies = cfg.get("companies", [])
    if not companies:
        print("No companies in config.", file=sys.stderr)
        return 1

    if args.check:
        return check(companies)

    jobs, errors = collect(companies)
    for e in errors:
        print(f"warning: {e}", file=sys.stderr)
    if len(errors) == len(companies):
        print("All companies failed - check your network or config.", file=sys.stderr)
        return 1

    matcher = filters.Matcher(cfg.get("search", {}))
    scored = [(s, j) for j in jobs if (s := matcher.score(j)) is not None]

    seen = store.load(args.state)
    new = [(s, j) for s, j in scored if j.key not in seen]
    new.sort(key=lambda x: (-x[0], x[1].company.lower(), x[1].title.lower()))

    cap = int(cfg.get("notify", {}).get("max_jobs_per_run", 30))
    batch = [j for _, j in new[:cap]]
    print(f"Fetched {len(jobs)} jobs, {len(scored)} match, {len(new)} new, sending {len(batch)}.")
    if not batch:
        return 0

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if args.dry_run or not (token and chat_id):
        if not args.dry_run:
            print("No Telegram credentials set - printing only, nothing saved.\n")
        print(notify.format_plain(batch))
        return 0

    for msg in notify.format_digest(batch):
        notify.send_telegram(token, chat_id, msg)

    today = date.today()
    for j in batch:
        seen[j.key] = today.isoformat()
    seen = store.prune(seen, {j.key for j in jobs}, today)
    store.save(args.state, seen)
    return 0


if __name__ == "__main__":
    sys.exit(main())
