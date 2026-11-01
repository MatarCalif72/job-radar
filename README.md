# job-radar

A small bot that checks company job boards **every 2 hours, all week**, and sends you
**one Telegram message per new matching job**.

Each message has: job title, company, place, a short summary, a "Good to know" box
(years of experience asked, which of your skills match, what else it asks for, hybrid/remote,
junior/student flag), the link, and a **⚙️ Redefine jobs** button.

- Reads public job APIs (Greenhouse, Lever, Ashby). No scraping, no accounts.
- Remembers what it already sent (`data/seen.json`), so no repeats.
- Runs free on GitHub Actions. Python 3.11+, no dependencies.
- Summaries are rule-based (no AI, no cost): quick pointers, not a replacement for reading the posting.

## Setup (10 minutes)

1. **Telegram bot:** message `@BotFather` → `/newbot` → copy the token.
   Send any message to your new bot, then open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `chat` → `id`.
2. **Companies:** edit `config.toml`. The slug is the name in the company's job-board URL
   (`boards.greenhouse.io/<slug>`, `jobs.lever.co/<slug>`, `jobs.ashbyhq.com/<slug>`).
   Check them: `python -m job_radar --check`
3. **Try it:** `python -m job_radar --dry-run` (prints messages, sends nothing).
4. **Deploy:** push to a GitHub repo → Settings → Secrets → Actions → add
   `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Run it once from the Actions tab.
5. **Turn on the Redefine page:** repo Settings → Pages → *Deploy from a branch* → `main` → folder `/docs`.
   Its address is `https://<your-name>.github.io/<repo>/` and the Telegram button opens it.

## Changing what you look for ("Redefine jobs")

Tap **⚙️ Redefine jobs** under any message. Answer four questions:

1. What do you want to work in? (type "QA" and the job titles fill in)
2. What level? (junior / mid / senior / any)
3. Where? (type "Tel Aviv" and nearby cities fill in)
4. Your skills

Edit any list (tap × to remove, type to add), then **Save** or **Save & run now**.
The first time, connect GitHub on that page (a token limited to this repo, stored only in your browser).
Your choices are saved to `my_search.json`, which overrides `[search]` and `[profile]` in `config.toml`.
Without GitHub connected, use **Copy JSON** and paste it into `my_search.json` yourself.

The page knows ~20 fields (QA, DevOps, backend, frontend, data, security, IT, product, design, sales...).
For anything else it uses your words as the title, and you add related titles by hand.
The filter reads job **titles** only.

Notes:
- New settings apply from the next run (every 2 hours), or right away with **Save & run now**.
- After changing direction, expect a batch of new jobs (up to 20 per run) until the backlog clears.
- The repo is public in the free setup, so `my_search.json` is visible to anyone who finds it.
  A private repo works too, but GitHub Pages needs a paid plan there; open `docs/index.html` on your computer instead
  and set `settings_button = false` in `config.toml`.
- Without Telegram credentials the bot only prints and saves nothing, so you never lose jobs.
- If Telegram fails halfway, unsent jobs are retried on the next run.
- GitHub's schedule can run a few minutes late. Mute the bot chat in Telegram for quiet nights.

## Tests

    python -m unittest discover -s tests -t .
    node tests/fields.test.js
