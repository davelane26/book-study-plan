#!/usr/bin/env python3
"""
Book Study Schedule Generator — "Basic Christian Teachings" by Zac Poonen
--------------------------------------------------------------------------
Run ONCE (not daily). It:
  1. Fetches the full book text from cfcindia.com (a single long page,
     all 72 chapters).
  2. Splits it into 72 chapters using the known chapter titles.
  3. Works out every Monday-Saturday date between today and Dec 31 of
     the current year.
  4. Spreads the entire book evenly across those days (splitting only at
     paragraph boundaries, never mid-sentence, and never altering the
     wording — required by the book's own copyright notice).
  5. Saves a single JSON file keyed by date, so send_daily_book_portion.py
     can just look up "today" and send that day's chunk.

This only needs to be run once per book. If you want to restart the
schedule (e.g. you fell behind and want to reset the pacing), just
re-run it — it will recompute from today's date forward.

Requirements:
  pip install requests beautifulsoup4

Copyright note: cfcindia.com explicitly grants permission for any part
of this book to be freely distributed, unaltered, with the author's name
and this copyright notice included. This script preserves the original
wording exactly and attaches that attribution to every daily portion —
see ATTRIBUTION_FOOTER below.
"""

import os
import re
import sys
import json
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

BOOK_URL = "https://www.cfcindia.com/books/basic-christian-teachings"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
SCHEDULE_PATH = os.path.join(OUTPUT_DIR, "book-schedule.json")

BOOK_TITLE = "Basic Christian Teachings"
BOOK_AUTHOR = "Zac Poonen"
ATTRIBUTION_FOOTER = (
    f"\n\n---\nFrom \"{BOOK_TITLE}\" by {BOOK_AUTHOR}. © 2024 by {BOOK_AUTHOR}. "
    f"Free distribution permitted, unaltered, with author's name and this "
    f"notice included. Source: {BOOK_URL}"
)

# The book's 72 chapter titles, in order, exactly as they appear as
# headings on the page (this is what we search for to split the text).
# If cfcindia.com ever revises this book's chapters, update this list.
CHAPTER_TITLES = [
    "The Origin Of Evil", "God Makes Evil Work For Good", "The Power Of Choice",
    "Sin Comes From Unbelief", "The Function Of Conscience", "Why Christ Has To Die",
    "Repentance", "Faith", "The Gift Of The Holy Spirit", "God\u2019s Word Is Our Food",
    "God\u2019s Word Helps Us Overcome Satan", "God\u2019s Word Renews Our Mind",
    "Religiosity And Spirituality", "Maximum Or Minimum For The Lord", "A Son Or A Servant",
    "Keeping The Tenth Commandment", "Dead Works", "More On Dead Works",
    "Some More On Dead Works", "Still More On Dead Works", "Law And Grace",
    "One Reason For Failure", "Another Reason For Failure", "More Reasons For Failure",
    "Faith And Praise", "Crucifixion And Praise", "Praise Drives Satan Out",
    "The New Song Of Praise", "Praise Brings Deliverance", "Praise Opens Closed Doors",
    "God\u2019s Purpose For Man", "Humility In Jesus Coming To Earth",
    "Humility In Jesus Earthly Life", "Humility In Jesus Death", "Jesus Overcame Sin",
    "Jesus Did God's Will", "Jesus Valued All People", "Jesus Valued People More Than Things",
    "Jesus Was Unpopular", "Jesus Obeyed The Father", "Jesus\u2019 speech was always loving",
    "Jesus\u2019 Gentleness and Goodness", "Finding Security In God As A Father",
    "God Can Give You Wisdom", "God And Money Are Opposites", "The Love Of Money Is Evil",
    "Give Back What Belongs To Others", "Giving Everything To God",
    "God Binds Husband And Wife Together", "Responsibilities Of Husband And Wife",
    "Bringing Up Godly Children", "Responsibilities Of Parents And Children",
    "Not Praying As Hypocrites Do", "Not Praying With Meaningless Repetition",
    "Praying Putting God First", "Praying About God\u2019s Interests",
    "Praying For Our Material Needs", "Praying For Our Spiritual Needs", "Hypocrisy",
    "Pride", "Selfishness", "Hatred", "Unbelief", "Unforgiveness And Bitterness", "Lying",
    "Don\u2019t Believe Satan\u2019s Lies", "Anger", "Proving God\u2019s Perfect Will (1)",
    "Proving God\u2019s Perfect Will (2)", "Proving God\u2019s Perfect Will (3)",
    "Submission To Authority", "God\u2019s Plan For Those Who Have Failed",
]


def fetch_book_soup():
    """Download the book page and return its parsed DOM."""
    resp = requests.get(BOOK_URL, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def _clean_text(el):
    """Get an element's text with inline tags joined by spaces, and any
    incidental whitespace/newlines (the page's HTML source is itself
    line-wrapped inside <p> tags) collapsed to single spaces."""
    return re.sub(r"\s+", " ", el.get_text(separator=" ", strip=True)).strip()


def split_into_chapters(soup):
    """Extract each chapter's title and paragraphs straight from the page's
    DOM (one <div class="chapter ..."> per chapter, holding an
    <h4 class="books-chapter-title"> heading and its <p> paragraphs).

    This reads real <p> boundaries as the paragraph breaks, rather than
    flattening the whole page to text first and re-deriving paragraphs by
    splitting on newlines — the source HTML has incidental line-wrapping
    newlines *inside* a single <p>, which a newline-split would wrongly
    treat as paragraph breaks and could scatter one sentence across two
    different days' chunks.
    """
    chapter_divs = soup.select("div.book-chapters div.chapter")
    if len(chapter_divs) != len(CHAPTER_TITLES):
        raise RuntimeError(
            f"Expected {len(CHAPTER_TITLES)} chapters, found {len(chapter_divs)}. "
            f"The book's page structure may have changed — check CHAPTER_TITLES "
            f"and the chapter div selector in this script."
        )

    chapters = []
    for i, (div, expected_title) in enumerate(zip(chapter_divs, CHAPTER_TITLES), start=1):
        heading = div.find("h4", class_="books-chapter-title")
        number_div = heading.find("div", class_="chapter-number") if heading else None
        title = ""
        if heading:
            number_text = _clean_text(number_div) if number_div else ""
            full_text = _clean_text(heading)
            title = full_text[len(number_text):].strip() if number_text else full_text

        if title != expected_title:
            raise RuntimeError(
                f"Chapter {i} heading is '{title}', expected '{expected_title}'. "
                f"The book's page structure or chapter titles may have changed — "
                f"update CHAPTER_TITLES in this script."
            )

        paragraphs = [_clean_text(p) for p in div.find_all("p")]
        paragraphs = [p for p in paragraphs if p]

        chapters.append({"number": i, "title": title, "paragraphs": paragraphs})

    return chapters


def paragraphs_with_chapter_labels(chapters):
    """Flatten all chapters into an ordered list of (chapter_num, chapter_title, paragraph_text).
    Paragraph boundaries come straight from the page's own <p> tags (see
    split_into_chapters), so no further splitting/merging is needed here."""
    flat = []
    for ch in chapters:
        for p in ch["paragraphs"]:
            flat.append((ch["number"], ch["title"], p))
    return flat


def get_study_dates():
    """Every Monday-Saturday date from today through Dec 31 of this year."""
    today = date.today()
    end = date(today.year, 12, 31)
    dates = []
    d = today
    while d <= end:
        if d.weekday() != 6:  # 6 = Sunday
            dates.append(d)
        d += timedelta(days=1)
    return dates


def distribute_across_days(flat_paragraphs, num_days):
    """Greedily bin the flattened paragraphs into num_days chunks, splitting
    only between paragraphs (never mid-sentence), aiming for even pacing."""
    total_words = sum(len(p[2].split()) for p in flat_paragraphs)
    days = []
    idx = 0
    n = len(flat_paragraphs)

    for day_num in range(num_days):
        remaining_days = num_days - day_num
        remaining_words = sum(len(p[2].split()) for p in flat_paragraphs[idx:])
        target = remaining_words / remaining_days if remaining_days else remaining_words

        bucket = []
        bucket_words = 0
        chapters_touched = set()

        while idx < n:
            ch_num, ch_title, para = flat_paragraphs[idx]
            para_words = len(para.split())
            # Always take at least one paragraph per day so no day is empty
            if bucket and bucket_words + para_words > target * 1.15:
                break
            bucket.append(para)
            chapters_touched.add((ch_num, ch_title))
            bucket_words += para_words
            idx += 1
            if bucket_words >= target:
                break

        if not bucket:
            break

        chapters_touched = sorted(chapters_touched)
        days.append({
            "text": "\n\n".join(bucket),
            "chapters": [{"number": c, "title": t} for c, t in chapters_touched],
        })

    # If any paragraphs are left over (rounding), append them to the last day
    if idx < n:
        leftover = flat_paragraphs[idx:]
        days[-1]["text"] += "\n\n" + "\n\n".join(p[2] for p in leftover)
        for c, t in {(p[0], p[1]) for p in leftover}:
            if not any(ch["number"] == c for ch in days[-1]["chapters"]):
                days[-1]["chapters"].append({"number": c, "title": t})
        days[-1]["chapters"].sort(key=lambda c: c["number"])

    return days


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Fetching book page...")
    soup = fetch_book_soup()
    print("  -> page fetched")

    print("Splitting into chapters...")
    chapters = split_into_chapters(soup)
    print(f"  -> {len(chapters)} chapters found")

    flat_paragraphs = paragraphs_with_chapter_labels(chapters)
    total_words = sum(len(p[2].split()) for p in flat_paragraphs)
    print(f"  -> {len(flat_paragraphs)} paragraphs, {total_words} words total")

    study_dates = get_study_dates()
    print(f"Spreading across {len(study_dates)} study days "
          f"({study_dates[0]} to {study_dates[-1]}, Mon-Sat only)...")

    day_chunks = distribute_across_days(flat_paragraphs, len(study_dates))

    schedule = {}
    for d, chunk in zip(study_dates, day_chunks):
        schedule[d.isoformat()] = chunk

    payload = {
        "book_title": BOOK_TITLE,
        "book_author": BOOK_AUTHOR,
        "source_url": BOOK_URL,
        "generated_on": date.today().isoformat(),
        "attribution_footer": ATTRIBUTION_FOOTER,
        "schedule": schedule,
    }

    with open(SCHEDULE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    avg_words = total_words / len(study_dates)
    print(f"Saved schedule to {SCHEDULE_PATH}")
    print(f"Average ~{avg_words:.0f} words/day across {len(study_dates)} days.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
