#!/usr/bin/env python3
"""
Daily book portion sender.
---------------------------
Run once per day, Monday through Saturday. Looks up today's date in
book-schedule.json (built by generate_book_schedule.py) and posts that
day's portion to Slack and/or Microsoft Teams via incoming webhooks.

Environment variables (set whichever you want to use — both is fine):
  SLACK_WEBHOOK_URL   - Slack incoming webhook URL
  TEAMS_WEBHOOK_URL   - Microsoft Teams incoming webhook URL
"""

import os
import sys
import json
from datetime import date

import requests

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
SCHEDULE_PATH = os.path.join(OUTPUT_DIR, "book-schedule.json")


def load_schedule():
    if not os.path.exists(SCHEDULE_PATH):
        raise RuntimeError(
            f"No schedule found at {SCHEDULE_PATH}. "
            f"Run generate_book_schedule.py first."
        )
    with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def format_message(payload, today_entry, today_str):
    chapters = today_entry["chapters"]
    if len(chapters) == 1:
        heading = f"Chapter {chapters[0]['number']}: {chapters[0]['title']}"
    else:
        span = ", ".join(f"{c['number']}" for c in chapters)
        heading = f"Chapters {span}: " + " / ".join(c["title"] for c in chapters)

    title_line = f"{payload['book_title']} — {today_str}"
    body = f"{title_line}\n{heading}\n\n{today_entry['text']}{payload['attribution_footer']}"
    return body


def send_to_slack(message):
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        print("SLACK_WEBHOOK_URL not set — skipping Slack.")
        return
    resp = requests.post(webhook, json={"text": message}, timeout=15)
    resp.raise_for_status()
    print("Sent to Slack.")


def send_to_teams(message):
    webhook = os.environ.get("TEAMS_WEBHOOK_URL")
    if not webhook:
        print("TEAMS_WEBHOOK_URL not set — skipping Teams.")
        return
    # Basic Teams "MessageCard" payload format for incoming webhooks
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": "Daily Book Study",
        "text": message,
    }
    resp = requests.post(webhook, json=payload, timeout=15)
    resp.raise_for_status()
    print("Sent to Teams.")


def main():
    payload = load_schedule()
    today_str = date.today().isoformat()

    today_entry = payload["schedule"].get(today_str)
    if today_entry is None:
        print(f"No study portion scheduled for {today_str} "
              f"(could be a Sunday, before the schedule's start date, or "
              f"after the schedule's last day).")
        return

    message = format_message(payload, today_entry, today_str)

    sent_anywhere = False
    if os.environ.get("SLACK_WEBHOOK_URL"):
        send_to_slack(message)
        sent_anywhere = True
    if os.environ.get("TEAMS_WEBHOOK_URL"):
        send_to_teams(message)
        sent_anywhere = True

    if not sent_anywhere:
        print("No webhook URLs configured — printing today's portion instead:\n")
        print(message)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
