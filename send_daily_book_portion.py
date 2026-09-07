#!/usr/bin/env python3
"""
Daily book portion sender.
---------------------------
Run once per day, Monday through Saturday. Looks up today's date in
book-schedule.json (built by generate_book_schedule.py) and posts that
day's portion to Slack and/or Microsoft Teams via incoming webhooks.
If SLACK_BOT_TOKEN and SLACK_CHANNEL_ID are set, also synthesizes an
MP3 narration of the day's text and uploads it to that Slack channel.

Environment variables (set whichever you want to use — mix and match):
  SLACK_WEBHOOK_URL   - Slack incoming webhook URL (posts the text)
  TEAMS_WEBHOOK_URL   - Microsoft Teams incoming webhook URL (posts the text)
  SLACK_BOT_TOKEN     - Slack bot token (xoxb-...) with files:write scope,
                        used to upload an audio (text-to-speech) version
  SLACK_CHANNEL_ID    - Slack channel ID (e.g. C0123ABC456) to upload the
                        audio file to; the bot must be a member of it
"""

import os
import sys
import json
import tempfile
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


def build_heading(chapters):
    if len(chapters) == 1:
        return f"Chapter {chapters[0]['number']}: {chapters[0]['title']}"
    span = ", ".join(f"{c['number']}" for c in chapters)
    return f"Chapters {span}: " + " / ".join(c["title"] for c in chapters)


def format_message(payload, today_entry, today_str):
    heading = build_heading(today_entry["chapters"])
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


def send_audio_to_slack(payload, today_entry, today_str):
    """Synthesize today's portion as speech and upload the MP3 to a Slack
    channel via the bot API (incoming webhooks can't attach files)."""
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    channel_id = os.environ.get("SLACK_CHANNEL_ID")
    if not bot_token or not channel_id:
        print("SLACK_BOT_TOKEN/SLACK_CHANNEL_ID not set — skipping audio upload.")
        return

    audio_path = None
    try:
        from gtts import gTTS
        from slack_sdk import WebClient

        heading = build_heading(today_entry["chapters"])

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            audio_path = f.name
        gTTS(text=today_entry["text"], lang="en").save(audio_path)

        client = WebClient(token=bot_token)
        client.files_upload_v2(
            channel=channel_id,
            file=audio_path,
            filename=f"{today_str}.mp3",
            title=f"{payload['book_title']} — {today_str}",
            initial_comment=f"\U0001F50A Audio version — {heading}",
        )
        print("Uploaded audio to Slack.")
    except Exception as e:
        # Don't let an audio hiccup fail the whole run — the text post
        # (if configured) already went out.
        print(f"WARNING: audio upload to Slack failed: {e}")
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


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
    if os.environ.get("SLACK_BOT_TOKEN") and os.environ.get("SLACK_CHANNEL_ID"):
        send_audio_to_slack(payload, today_entry, today_str)
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
