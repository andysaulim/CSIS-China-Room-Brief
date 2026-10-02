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

from brief import archive, collect, compose, congress, enrich, mailer, qa, render, tracker
from brief import horizon as hz
from brief.issue import assemble, csis_style, label

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
    read = enrich.research(research)
    print(f"research pages read: {read} of {len(research)}")
    by_inst = {}
    for x in research:
        by_inst[x["institution"]] = by_inst.get(x["institution"], 0) + 1
    print("research by institution: " + (", ".join(f"{k} {v}" for k, v in sorted(by_inst.items())) or "none"))
    pri = [x for x in news if x.get("outlet")]
    print(f"priority-outlet items: {len(pri)}, with publisher headline: "
          f"{sum(1 for x in pri if x.get('original_headline'))}")
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
    print(f"committee releases: {len(hill)}")
    items, audit = load_tracker()
    upcoming = collect.daily_upcoming(end)
    week = hz.glance(hz.from_tracker(items, issue_date) + upcoming + hz.from_docket(dk, issue_date), issue_date)
    this_week = sum(e["window"] == "this week" for e in week)
    print(f"calendar entries for Week at a Glance: {this_week} this week, {len(week) - this_week} the week after")

    copy = compose.draft(news, research, week, f"{label(start)} to {label(end)}", style)
    copy["hill_docket"] = dk
    for sec in ("research_roundup", "heard_on_the_hill"):
        for it in copy.get(sec, []):
            it["url"] = collect.publisher_url(it["url"])
    copy["qa"] = qa.check(csis_style(copy), (start, end), calendar_count=len(week))
    print("checks:\n  " + "\n  ".join(copy["qa"] or ["none"]))
    ISSUES.mkdir(exist_ok=True)
    f = ISSUES / f"{issue_date.isoformat()}.json"
    # Fields an editor fixed by hand and listed under "keep" survive a re-run.
    if f.exists():
        prior = json.loads(f.read_text(encoding="utf-8"))
        for k in prior.get("keep", []):
            if k in prior:
                copy[k] = prior[k]
        if prior.get("keep"):
            copy["keep"] = prior["keep"]
            copy["qa"] = [q for q in copy.get("qa", []) if not (q.startswith("Editor's note") and "editors_note" in prior["keep"])]
            print("kept from the edited copy: " + ", ".join(prior["keep"]))
    f.write_text(json.dumps(copy, ensure_ascii=False, indent=1), encoding="utf-8")

    notes = []
    if missing:
        notes.append("Daily brief issues missing for " + ", ".join(missing) + ".")
    notes += copy.get("warnings", [])
    issue = assemble(copy, items, issue_date, (start, end), issue_label="Draft", banner_src=BANNER,
                     daily_upcoming=upcoming,
                     research_note=" ".join(notes) or "Check each item on its page before send.",
                     candidates={"hill": [], "glance": [
                         {"text": e["title"], "date_label": compose._span(e["start"], e["end"]),
                          "source": e["source"], "url": e.get("url", "")}
                         for e in week if e["title"] not in {g.get("calendar_title") for g in copy["week_at_a_glance"]}][:6]})
    html = render.render(issue, "draft", os.environ.get("BRIEF_THEME", "briefing"))
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out" / f"draft_{issue_date.isoformat()}.html").write_text(html, encoding="utf-8")
    sent = mailer.send(html, f"[DRAFT] China Room Brief, {label(issue_date)}: {copy['re_line']}", "DRAFT_TO", BANNER)
    print(f"draft for {issue_date}: {len(news)} news, {len(research)} research, "
          f"{len(dk.get('hearings', []))} hearings, {len(dk.get('bills', []))} new bills"
          f"{'' if os.environ.get('CONGRESS_API_KEY') else ' (no CONGRESS_API_KEY)'}, "
          f"{len(audit)} tracker findings, sent to {len(sent)}")


def cmd_send(issue_date: date) -> None:
    f = ISSUES / f"{issue_date.isoformat()}.json"
    if not f.exists():
        sys.exit(f"No draft for {issue_date} yet ({f.name} not found). Run the workflow in draft mode first, "
                 f"then send.")
    copy = json.loads(f.read_text(encoding="utf-8"))
    items, _ = load_tracker()
    n = len(sorted(ISSUES.glob("*.json")))
    issue = assemble(copy, items, issue_date, window(issue_date), issue_label=f"No. {n}", banner_src=BANNER,
                     daily_upcoming=collect.daily_upcoming(issue_date))
    html = render.render(issue, "final", os.environ.get("BRIEF_THEME", "briefing"))
    archive.publish(ROOT / "site", issue_date.isoformat(), html,
                    {"date_line": issue["date_line"], "label": f"No. {n}", "re_line": issue["re_line"]})
    sent = mailer.send(html, f"China Room Brief, {label(issue_date)}: {copy['re_line']}", "BRIEF_TO", BANNER)
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
