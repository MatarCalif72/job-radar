# job-radar

Personal job-alert bot. Checks company job boards every 2 hours, filters for relevant jobs,
and sends **one Telegram message per new job** (title, company, place, short summary,
"Good to know" box, link, and a "Redefine jobs" button). Runs free on GitHub Actions.

- GitHub repo: `MatarCalif72/job-radar` (public, branch `main`)
- Local folder: `C:\Users\matar\OneDrive\Desktop\job-radar` (NOT a git repo yet, see "Open items")
- Owner prefers short, plain-language answers.

## How it works
1. `config.toml` lists companies (`ats` = greenhouse | greenhouse-eu | lever | ashby, plus `slug`) and the default `[search]` / `[profile]` / `[notify]` settings.
2. `companies_found.json` (written by `python -m job_radar --discover`) adds boards found automatically from `discovery_names.txt`. They are merged with the config list.
3. `my_search.json` (written by the Redefine page in `docs/`) overrides `[search]` and `[profile]`.
4. `job_radar/sources.py` fetches jobs + descriptions. `filters.py` matches by TITLE and location. `insights.py` builds the summary and "Good to know" lines (rule-based, no AI).
5. `data/seen.json` remembers sent jobs. `notify.py` sends to Telegram.
6. Workflows in `.github/workflows/`: `job-radar.yml` (every 2h, all week) and `discover.yml` (manual + weekly). Both commit their result files back to the repo.

## Commands
- Tests: `python -m unittest discover -s tests -t .` and `node tests/fields.test.js`
- Preview without sending: `python -m job_radar --dry-run`
- Check company boards: `python -m job_radar --check`
- Find boards from names: `python -m job_radar --discover`
- Needs Python 3.11+ (uses `tomllib`). Standard library only, no pip packages.

## Rules
- Telegram credentials are GitHub secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. NEVER put them in any file or commit.
- `data/seen.json` is written by the bot. Do not overwrite it with an empty one (it would resend old jobs).
- The page in `docs/` (served by GitHub Pages from `/docs`) saves `my_search.json` through the GitHub API with a token kept only in the browser.

## Open items
- Local folder has no `.git`. Connect it to the GitHub repo (git init, remote add origin, fetch, `git reset origin/main`, then `git checkout origin/main -- data/seen.json`, add, commit, push). Delete the stray old `job-radar/job-radar` subfolder first.
- `.github/workflows/discover.yml` must exist in the repo (tools could not write into `.github` on Windows).
- Run **discover-companies** in the Actions tab, read the log (`FOUND` lines and the "No board found" list), then run **job-radar**.
- If many wanted companies land in "No board found" (Comeet, Workable or own career sites), add support for those job systems.
- Not verified against the real services (the build environment was offline): the board names in `config.toml` (only Snyk confirmed), and the `greenhouse-eu` API address.
- Possible later: several saved searches (different level/place per job type, tag each message with its search).

## Known limits
- Filters read job titles only, not descriptions.
- Summary and "Good to know" are simple rules, so they can be imperfect.
- An IT/helpdesk search returned 0 matches on the first 5 companies (mostly security/fintech startups), which is expected.
