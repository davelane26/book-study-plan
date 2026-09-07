# Book Study Plan — "Basic Christian Teachings" — Automated, Slack/Teams

Spreads Zac Poonen's book *Basic Christian Teachings* evenly across every
Monday–Saturday from today through December 31, and delivers one portion
per day automatically to Slack and/or Microsoft Teams.

## How it works

**`generate_book_schedule.py`** (run ONCE):
1. Fetches the full book text from cfcindia.com (it's one long page with
   all 72 chapters).
2. Splits it into chapters using the known chapter titles.
3. Works out every Monday–Saturday date between today and Dec 31.
4. Spreads the whole book evenly across those days — splitting only
   between paragraphs, never mid-sentence, so the wording is never
   altered (see Copyright note below).
5. Saves `output/book-schedule.json`, keyed by date.

**`send_daily_book_portion.py`** (runs every morning, Mon–Sat):
1. Looks up today's date in the schedule.
2. Posts that day's chunk (with a chapter heading and attribution
   footer) to Slack and/or Teams, via incoming webhooks.

## Copyright note

cfcindia.com's own copyright notice for this book explicitly permits
free distribution of any part of it, provided: no alterations are made,
the author's name is included, and the copyright notice is included in
each printout. This script honors all three: it never rewords or
truncates mid-sentence, and every daily message ends with an attribution
footer naming the author and linking back to the source.

## One-time setup (about 15 minutes)

### 1. Get a Slack and/or Teams webhook URL

**Slack:** Go to [api.slack.com/apps](https://api.slack.com/apps) →
create an app (or use an existing one) → "Incoming Webhooks" → activate
it → "Add New Webhook to Workspace" → pick the channel → copy the URL.

**Teams:** In the target channel, click "..." → **Connectors** (or
**Workflows** on newer Teams) → search for "Incoming Webhook" → configure
it → copy the URL. (Microsoft has been migrating from classic
Connectors to Workflows-based webhooks; if the classic one isn't
available in your tenant, search Teams docs for "Workflows incoming
webhook" — the payload format in `send_daily_book_portion.py` may need
minor adjustment for that path.)

### 2. Create a GitHub repo
- Create a new repo (can be private).
- Add all files in this folder: `generate_book_schedule.py`,
  `send_daily_book_portion.py`, `requirements.txt`,
  `.github/workflows/generate-schedule.yml`,
  `.github/workflows/daily-book-portion.yml`, this `README.md`.
- Create the empty `output/` folder (add `output/.gitkeep`).

### 3. Add your secrets
In the repo: **Settings → Secrets and variables → Actions → New repository secret**.

- `SLACK_WEBHOOK_URL` — if using Slack
- `TEAMS_WEBHOOK_URL` — if using Teams

(You can set one, or both.)

### 4. Generate the schedule (run once)
Go to **Actions → "Generate Book Study Schedule" → Run workflow**.
This builds `output/book-schedule.json` covering every Mon–Sat date from
today through Dec 31, and commits it to the repo. You only need to do
this once — re-run it later only if you want to reset the pacing from a
new start date.

### 5. Confirm the daily send schedule
`daily-book-portion.yml` runs at **7:00 AM Mountain Time, Monday through
Saturday**. Daylight saving shifts this by an hour part of the year —
adjust the cron hour by 1 if you want it pinned exactly.

### 6. Test it once manually
Go to **Actions → "Daily Book Study Portion" → Run workflow** to confirm
today's portion actually posts to Slack/Teams. (It'll say "no portion
scheduled" if you test on a day outside the generated range.)

## Running it locally (optional, for testing)

```bash
pip install -r requirements.txt
python generate_book_schedule.py

export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
export TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...
python send_daily_book_portion.py
```

## Known limitations

- **This only works for this specific book's page structure.** The
  chapter-splitting logic looks for `"Chapter N <title>"` headings using
  a hardcoded list of the 72 chapter titles. If cfcindia.com ever
  revises this book, update `CHAPTER_TITLES` in
  `generate_book_schedule.py`.
- **Day sizes vary a bit.** Chapters aren't all the same length, so some
  days get more or less text — the script paces by total word count, not
  a fixed page/word count per day, per your request to spread it evenly
  over however many days are left in the year.
- **If a day's send fails** (e.g. a webhook is temporarily down), that
  day's portion is not automatically resent — you'd need to trigger that
  day's workflow run manually, or wait for GitHub's own retry behavior
  if any.
- **Only Monday–Saturday dates get portions.** Sundays are intentionally
  skipped in the schedule.
