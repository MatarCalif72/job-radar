# job-radar

A small bot that checks company job boards every morning and sends you **only new, matching jobs** on Telegram.

- Reads public job APIs (Greenhouse, Lever, Ashby). No scraping, no accounts.
- Filters by title, seniority and location (see `config.toml`). Junior roles rank first.
- Remembers what it already sent (`data/seen.json`), so no repeats.
- Runs free on GitHub Actions, Sunday–Thursday morning. Python 3.11+, no dependencies.

## Setup (10 minutes)

1. **Telegram bot:** message `@BotFather` → `/newbot` → copy the token.
   Send any message to your new bot, then open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `chat` → `id`.
2. **Companies:** edit `config.toml`. The slug is the name in the company's job-board URL
   (`boards.greenhouse.io/<slug>`, `jobs.lever.co/<slug>`, `jobs.ashbyhq.com/<slug>`).
   Check them: `python -m job_radar --check`
3. **Try it:** `python -m job_radar --dry-run` (prints matches, sends nothing).
4. **Deploy:** push to a GitHub repo → Settings → Secrets → Actions → add
   `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Run it once from the Actions tab.

Without Telegram credentials it only prints and saves nothing, so you never lose jobs.

## Tests

    python -m unittest discover -s tests -t .

## Ideas for later

More sources (Comeet, Workable), a score based on your CV keywords, a weekly summary.
