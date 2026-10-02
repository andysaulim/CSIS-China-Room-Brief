"""CSIS China Room Brief: weekly run.

    python weekly.py draft  [--issue-date YYYY-MM-DD] [--style house|brevity]
    python weekly.py send   [--issue-date YYYY-MM-DD]

draft (Thursday noon): collects the past week from the China Daily Brief
archive, think-tank and CRS feeds, and the ER tracker; drafts the copy with
Claude; saves it to issues/YYYY-MM-DD.json; emails the draft to DRAFT_TO.
The coordinator edits issues/YYYY-MM-DD.json (GitHub's web editor is fine).

send (Friday morning): renders the edited copy against a fresh pull of the
tracker, emails it to BRIEF_TO, and writes the web copy and archive to site/.

Environment: ANTHROPIC_API_KEY, GMAIL_USER, GMAIL_APP_PASS, GMAIL_FROM,
DRAFT_TO, BRIEF_TO, TRACKER_URL, CONGRESS_API_KEY, BANNER_URL, and optionally
CHINA_ROOM_WEB_BASE and CHINA_ROOM_CALENDAR_URL.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

from brief import archive, collect, compose, congress, mailer, render, tracker
from brief.issue import assemble, label

ROOT = Path(__file__).parent
ISSUES = ROOT / "issues"
BANNER = os.environ.get(
    "BANNER_URL",
    "https://raw.githubusercontent.com/andysaulim/CSIS-China-Room-Brief/HEAD/assets/banner_china_room.png")


def next_friday(today: date) -> date:
    return today + timedelta(days=(4 - today.weekday()) % 7)


def window(issue_date: date) -> tuple[date, date]:
    """The seven days ending the day before the draft: Friday through Thursday."""
    return issue_date - timedelta(days=7), issue_date - timedelta(days=1)


def load_tracker():
    url = os.environ.get("TRACKER_URL", "")
    if not url:
        sys.exit("TRACKER_URL is not set")
    path = collect.tracker_file(url, os.path.join(tempfile.gettempdir(), "tracker.xlsx"))
    if not path:
        sys.exit("could not download the tracker (is it shared by link, and is the URL a direct download?)")
    items, skipped = tracker.load(path)
    return items, tracker.audit(path, items) + skipped


def cmd_draft(issue_date: date, style: str) -> None:
    start, end = window(issue_date)
    news, missing = collect.daily_items(start, end)
    collect.tag_outlets(news)
    research = collect.research_items(start, end)
    dk = congress.docket((start, end))
    for h in dk.get("hearings", []):
        news.append({"date": h["date"], "section": "Congress.gov hearing", "tag": h["committee"],
                     "headline": h["title"], "body": f'{h["type"]} ({h["status"]}), {h["chamber"]}',
                     "url": h["url"]})
    for b in dk.get("bills", []):
        news.append({"date": b["introduced"], "section": "Congress.gov new bill",
                     "tag": f'{b["number"]}, {b["sponsor"]}', "headline": b["title"],
                     "body": f'Introduced {b["introduced"]}', "url": b["url"]})
    items, audit = load_tracker()
    cal = [f"{i.date_label}: {i.name}" for i in tracker.week_ahead(items, issue_date + timedelta(days=1))]

    copy = compose.draft(news, research, cal, f"{label(start)} to {label(end)}", style)
    copy["hill_docket"] = dk
    ISSUES.mkdir(exist_ok=True)
    f = ISSUES / f"{issue_date.isoformat()}.json"
    f.write_text(json.dumps(copy, ensure_ascii=False, indent=1), encoding="utf-8")

    notes = []
    if missing:
        notes.append("Daily brief issues missing for " + ", ".join(missing) + ".")
    notes += copy.get("warnings", [])
    issue = assemble(copy, items, issue_date, (start, end), issue_label="Draft", banner_src=BANNER,
                     research_note=" ".join(notes) or "Check each item on its page before send.",
                     candidates={"hill": [], "glance": []})
    html = render.render(issue, "draft", os.environ.get("BRIEF_THEME", "newsroom"))
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out" / f"draft_{issue_date.isoformat()}.html").write_text(html, encoding="utf-8")
    sent = mailer.send(html, f"[DRAFT] China Room Brief, {label(issue_date)}: {copy['re_line']}", "DRAFT_TO")
    print(f"draft for {issue_date}: {len(news)} news, {len(research)} research, "
          f"{len(audit)} tracker findings, sent to {len(sent)}")


def cmd_send(issue_date: date) -> None:
    f = ISSUES / f"{issue_date.isoformat()}.json"
    if not f.exists():
        sys.exit(f"{f} not found; run the draft first")
    copy = json.loads(f.read_text(encoding="utf-8"))
    items, _ = load_tracker()
    n = len(sorted(ISSUES.glob("*.json")))
    issue = assemble(copy, items, issue_date, window(issue_date), issue_label=f"No. {n}", banner_src=BANNER)
    html = render.render(issue, "final", os.environ.get("BRIEF_THEME", "newsroom"))
    archive.publish(ROOT / "site", issue_date.isoformat(), html,
                    {"date_line": issue["date_line"], "label": f"No. {n}", "re_line": issue["re_line"]})
    sent = mailer.send(html, f"China Room Brief, {label(issue_date)}: {copy['re_line']}", "BRIEF_TO")
    print(f"sent {issue_date} to {len(sent)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["draft", "send"])
    ap.add_argument("--issue-date", default="")
    ap.add_argument("--style", default="house", choices=list(compose.STYLE))
    a = ap.parse_args()
    d = date.fromisoformat(a.issue_date) if a.issue_date else next_friday(date.today())
    cmd_draft(d, a.style) if a.mode == "draft" else cmd_send(d)


if __name__ == "__main__":
    main()
