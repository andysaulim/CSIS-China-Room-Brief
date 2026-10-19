"""CSIS China Room Engagement Brief: weekly run.

    python weekly.py sweep  [--issue-date YYYY-MM-DD]
    python weekly.py draft  [--issue-date YYYY-MM-DD] [--style house|brevity]
    python weekly.py send   [--issue-date YYYY-MM-DD]

sweep (Sunday evening): reads Brian's X accounts, pulls the week's posts,
groups them into topics and writes candidates to the approvals sheet for
Talk Around Town. Brian marks Approve or Reject on Monday morning.

draft (Monday noon): Talk Around Town from the approved topics; Heard on the
Hill from Congress.gov, committee releases and approved outlets; CSIS Impact
from csis.org and the engagement form; In the Works and On the Horizon from
Brian's sheets. Saves issues/YYYY-MM-DD.json and emails the draft to DRAFT_TO.

send (Tuesday morning): renders the saved copy against fresh sheets and
approvals, emails it to BRIEF_TO, and writes the web copy to site/.

Environment: ANTHROPIC_API_KEY, GMAIL_USER, GMAIL_APP_PASS, GMAIL_FROM,
DRAFT_TO, BRIEF_TO, CONGRESS_API_KEY, GOOGLE_SERVICE_ACCOUNT_JSON, APIFY_TOKEN,
APIFY_ACTOR, X_ACCOUNTS_URL, APPROVALS_SHEET_URL, ENGAGEMENTS_URL, WORKS_URL,
HORIZON_URL, HORIZON_VIEW_URL, CHINA_ROOM_CALENDAR_URL, TRACKER_URL (fallback
for the two calendar sheets), BANNER_URL, CHINA_ROOM_WEB_BASE.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import re
import tempfile
from datetime import date, timedelta
from pathlib import Path

from brief import archive, collect, compose, congress, enrich, forms, mailer, qa, render, sheets, tracker, x_sweep
from brief.issue import assemble, csis_style, label

ROOT = Path(__file__).parent
ISSUES = ROOT / "issues"
BANNER = os.environ.get(
    "BANNER_URL",
    "https://raw.githubusercontent.com/andysaulim/CSIS-China-Room-Brief/HEAD/assets/banner_china_room.png")


def next_tuesday(today: date) -> date:
    return today + timedelta(days=(1 - today.weekday()) % 7)


def window(issue_date: date) -> tuple[date, date]:
    """The seven days ending the day before the issue: Tuesday through Monday."""
    return issue_date - timedelta(days=7), issue_date - timedelta(days=1)


NAME = "China Room Engagement Brief"


def load_calendars():
    """In the Works and On the Horizon rows from Brian's sheets (TRACKER_URL tabs as the fallback)."""
    items, audit = [], []
    sources = [(os.environ.get("WORKS_URL", ""), "works"), (os.environ.get("HORIZON_URL", ""), "horizon")]
    if not any(u for u, _ in sources):
        sources = [(os.environ.get("TRACKER_URL", ""), None)]
    for url, role in sources:
        if not url:
            continue
        path = sheets.xlsx(url, os.path.join(tempfile.gettempdir(), f"{role or 'tracker'}.xlsx"))
        if not path:
            audit.append(f"SHEET_UNAVAILABLE: {role or 'tracker'}")
            continue
        print(f"{role or 'tracker'} sheet tabs:\n  " + "\n  ".join(tracker.describe(path)))
        got, skipped = tracker.load(path, role)
        items += got
        audit += skipped
    return items, audit


def calendar_url(env: str, fallback_env: str) -> str:
    """A view link for a sheet: the explicit one, else the sheet's own edit page."""
    url = os.environ.get(env, "").strip()
    sid = sheets.sheet_id(os.environ.get(fallback_env, "") or os.environ.get("TRACKER_URL", ""))
    return url or (f"https://docs.google.com/spreadsheets/d/{sid}/edit" if sid else "")


def keep_edits(f: Path, copy: dict) -> None:
    """Fields an editor fixed by hand and listed under "keep" survive a re-run."""
    if not f.exists():
        return
    prior = json.loads(f.read_text(encoding="utf-8"))
    for k in prior.get("keep", []):
        if k in prior:
            copy[k] = prior[k]
    if prior.get("keep"):
        copy["keep"] = prior["keep"]
        print("kept from the edited copy: " + ", ".join(prior["keep"]))


def cmd_sweep(issue_date: date) -> None:
    missing = [k for k in ("APIFY_TOKEN", "X_ACCOUNTS_URL", "APPROVALS_SHEET_URL", "GOOGLE_SERVICE_ACCOUNT_JSON")
               if not os.environ.get(k)]
    if missing:
        print("sweep skipped; not set up yet: " + ", ".join(missing))
        return
    found = x_sweep.sweep(issue_date)
    for t in found:
        print(f"  {t['score']:>8}  {t['title']}  ({', '.join(t['accounts'][:4])})")


def cmd_draft(issue_date: date, style: str) -> None:
    start, end = window(issue_date)
    # Heard on the Hill: Congress.gov, committee releases, and Congress coverage in the daily brief
    news, missing = collect.daily_items(start, end)
    collect.tag_outlets(news, fetch_titles=False)
    dk = congress.docket((start, end))
    for h in dk.get("hearings", []):
        news.append({"date": h["date"], "section": "Congress.gov hearing", "tag": h["committee"],
                     "headline": h["title"], "body": f'{h["type"]} ({h["status"]}), {h["chamber"]}',
                     "url": h["url"]})
    for b in dk.get("bills", []):
        news.append({"date": b["introduced"], "section": "Congress.gov new bill",
                     "tag": f'{b["number"]}, {b["sponsor"]}', "headline": b["title"],
                     "body": f'Introduced {b["introduced"]}', "url": b["url"]})
    hill = collect.hill_releases(start, end)
    news += hill
    print(f"news items: {len(news)} ({len(hill)} committee releases)")
    # CSIS Impact
    research = collect.csis_research(start, end)
    read = enrich.research(research)
    print(f"CSIS publications: {len(research)}, pages read: {read}")
    engaged = forms.engagements(os.environ.get("ENGAGEMENTS_URL", ""), start, end)
    print(f"engagement form submissions in the week: {len(engaged)}")
    # Talk Around Town
    talk, note = x_sweep.approved(issue_date)
    print(f"Talk Around Town: {note}")
    # Calendars
    items, audit = load_calendars()

    copy = compose.draft(news, research, engaged, f"{label(start)} to {label(end)}", style)
    copy["talk_around_town"] = talk
    copy["hill_docket"] = dk
    for it in copy["heard_on_the_hill"]:
        it["url"] = collect.publisher_url(it["url"])
    copy["qa"] = qa.check(csis_style(copy), (start, end))
    if not talk or not all(t.get("approved") for t in talk):
        copy["qa"].insert(0, f"Talk Around Town: {note}.")
    if any(a.startswith("SHEET_UNAVAILABLE") for a in audit):
        copy["qa"].insert(0, "A calendar sheet could not be read: " + ", ".join(
            a.split(": ")[1] for a in audit if a.startswith("SHEET_UNAVAILABLE")) + ".")
    print("checks:\n  " + "\n  ".join(copy["qa"] or ["none"]))
    ISSUES.mkdir(exist_ok=True)
    f = ISSUES / f"{issue_date.isoformat()}.json"
    keep_edits(f, copy)
    f.write_text(json.dumps(copy, ensure_ascii=False, indent=1), encoding="utf-8")

    issue = assemble(copy, items, issue_date, (start, end), issue_label="Draft", banner_src=BANNER,
                     daily_upcoming=collect.daily_upcoming(end))
    issue["calendar_url"] = calendar_url("CHINA_ROOM_CALENDAR_URL", "WORKS_URL")
    issue["horizon_url"] = calendar_url("HORIZON_VIEW_URL", "HORIZON_URL")
    html = render.render(issue, "draft", os.environ.get("BRIEF_THEME", "briefing"))
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out" / f"draft_{issue_date.isoformat()}.html").write_text(html, encoding="utf-8")
    sent = mailer.send(html, f"[DRAFT] {NAME}, {label(issue_date)}", "DRAFT_TO", BANNER)
    print(f"draft for {issue_date}: {len(talk)} talk, {len(copy['heard_on_the_hill'])} hill, "
          f"{len(copy['csis_impact']['research'])} research, {len(copy['csis_impact']['engagements'])} engagements, "
          f"{len(issue['in_the_works']['items'])} in the works, {len(issue['on_the_horizon']['near'])} horizon, "
          f"sent to {len(sent)}")


def cmd_send(issue_date: date) -> None:
    f = ISSUES / f"{issue_date.isoformat()}.json"
    if not f.exists():
        sys.exit(f"No draft for {issue_date} yet ({f.name} not found). Run the workflow in draft mode first, "
                 f"then send.")
    copy = json.loads(f.read_text(encoding="utf-8"))
    talk, note = x_sweep.approved(issue_date)          # pick up approvals made after the draft
    if talk and all(t.get("approved") for t in talk) and "talk_around_town" not in copy.get("keep", []):
        copy["talk_around_town"] = talk
    # never send a topic Brian has not approved
    copy["talk_around_town"] = [t for t in copy.get("talk_around_town", []) if t.get("approved", True)]
    print(f"Talk Around Town at send: {len(copy['talk_around_town'])} approved ({note})")
    items, _ = load_calendars()
    n = len(sorted(ISSUES.glob("*.json")))
    issue = assemble(copy, items, issue_date, window(issue_date), issue_label=f"No. {n}", banner_src=BANNER,
                     daily_upcoming=collect.daily_upcoming(issue_date))
    issue["calendar_url"] = calendar_url("CHINA_ROOM_CALENDAR_URL", "WORKS_URL")
    issue["horizon_url"] = calendar_url("HORIZON_VIEW_URL", "HORIZON_URL")
    html = render.render(issue, "final", os.environ.get("BRIEF_THEME", "briefing"))
    archive.publish(ROOT / "site", issue_date.isoformat(), html,
                    {"date_line": issue["date_line"], "label": f"No. {n}", "re_line": ""})
    sent = mailer.send(html, f"{NAME}, {label(issue_date)}", "BRIEF_TO", BANNER)
    print(f"sent {issue_date} to {len(sent)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["sweep", "draft", "send"])
    ap.add_argument("--issue-date", default="")
    ap.add_argument("--style", default="house", choices=list(compose.STYLE))
    a = ap.parse_args()
    d = date.fromisoformat(a.issue_date) if a.issue_date else next_tuesday(date.today())
    {"sweep": lambda: cmd_sweep(d), "draft": lambda: cmd_draft(d, a.style), "send": lambda: cmd_send(d)}[a.mode]()


if __name__ == "__main__":
    main()
