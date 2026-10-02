"""Build Issue 0 (Tuesday, Oct 6, 2026) from real inputs.

    python build_sample.py --tracker data/CSIS_US_China_Tracker.xlsx \
        --ledger path/to/Daily-China-Digest/published_ledger.json

Inputs:
  samples/issue0_copy.json  the written sections. Every sentence traces to a
                            China Daily Brief item (Sep 28 to Oct 2) or to a
                            publication page; Research Roundup items were
                            confirmed by search results only.
  the ER tracker            In the Works and On the Horizon, read at build time
  the daily ledger          candidate lists shown in the draft

Outputs in out/: the Monday-noon draft, the Tuesday email, the tracker audit,
and site/ (index.html, 2026-10-06.html, archive.html, archive.json).

Set CHINA_ROOM_WEB_BASE to the archive's public URL so Read online and Past
issues resolve from an inbox; without it they are relative, for local preview.
"""

import argparse
import json
import os
from datetime import date
from pathlib import Path

from brief import archive, daily_feed, render, tracker

ISSUE = date(2026, 10, 6)
BACK = (date(2026, 9, 28), date(2026, 10, 4))
# The tracker's share link is not kept in this public repository.
CALENDAR_URL = os.environ.get("CHINA_ROOM_CALENDAR_URL", "")
WEB_BASE = os.environ.get("CHINA_ROOM_WEB_BASE", "").rstrip("/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracker", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--copy", default="samples/issue0_copy_house.json")
    ap.add_argument("--suffix", default="", help="added to output file names, e.g. _brevity")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()

    copy = json.loads(Path(a.copy).read_text(encoding="utf-8"))
    items, skipped = tracker.load(a.tracker)
    ledger = daily_feed.in_window(daily_feed.load_ledger(a.ledger), *BACK)

    def cand(x):
        d = date.fromisoformat(x["date"])
        return {"text": x["headline"], "url": x["url"], "source": x["outlet"],
                "date_label": f'{d.strftime("%b")} {d.day}'}

    def chip(i):
        if i.precision == "month":
            return i.start.strftime("%b").upper(), "TBC" if i.tentative else ""
        day = str(i.start.day) if i.start == i.end else f"{i.start.day}–{i.end.day}"
        return i.start.strftime("%b").upper(), day

    def where(desc):
        cuts = [desc.find(sep) for sep in (" — ", " - ", " (") if sep in desc]
        return desc[:min(cuts)].strip() if cuts else desc[:90]

    works = [{"month": chip(i)[0], "day": chip(i)[1], "headline": i.name,
              "detail": i.description, "url": i.link}
             for i in tracker.in_the_works(items, ISSUE, limit=5)]
    horizon = [{"month": chip(i)[0], "day": chip(i)[1], "headline": i.name,
                "detail": where(i.description), "url": i.link}
               for i in tracker.on_the_horizon(items, ISSUE)]

    iso = ISSUE.isoformat()
    issue = {
        "date_line": "Tuesday, October 6, 2026",
        "issue_label": "Issue 0 · sample",
        "draft_for": "Nina Prieur · Monday noon",
        "calendar_url": CALENDAR_URL,
        "web_url": f"{WEB_BASE}/{iso}.html" if WEB_BASE else f"site/{iso}.html",
        "archive_url": f"{WEB_BASE}/archive.html" if WEB_BASE else "site/archive.html",
        "re_line": copy["re_line"],
        "editors_note": copy["editors_note"],
        "bottom_line": copy.get("bottom_line", ""),
        "back_window": "Sep 28 to Oct 4",
        "ahead_window": "Oct 6 onward",
        "week_at_a_glance": {
            "items": copy["week_at_a_glance"],
            "spec": "Draft above. Rewrite or swap from the tracker and daily-brief candidates below.",
            "candidates": [{"text": i.name, "url": i.link, "date_label": i.date_label,
                            "source": "tracker"} for i in tracker.week_ahead(items, ISSUE)]
                          + [cand(x) for x in daily_feed.forward_candidates(ledger)[:4]],
        },
        "heard_on_the_hill": {
            "items": copy["heard_on_the_hill"],
            "big_picture": copy.get("heard_on_the_hill_big_picture", ""),
            "spec": "Draft above, from the daily brief's Congress items. Add hearings and floor action it missed.",
            "candidates": [cand(x) for x in daily_feed.hill_candidates(ledger)],
        },
        "in_the_news": copy["in_the_news"],
        "research_roundup": {
            "items": copy["research_roundup"],
            "big_picture": copy.get("research_roundup_big_picture", ""),
            "spec": "Verify each item on its page before send.",
            "gap": "Found by search; the publication pages could not be opened from the build "
                   "machine. No CRS China product was found dated Sep 28 to Oct 2.",
        },
        "in_the_works": {"items": works},
        "on_the_horizon": {"items": horizon},
        "contact": copy["contact"],
        "footer": ("The China Room Brief is compiled by CSIS External Relations. Look-back items draw on the "
                   "CSIS China Daily Brief; calendar items come from the China Room editorial calendar."),
    }

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sfx = a.suffix
    (out / f"draft_{iso}{sfx}.html").write_text(render.render(issue, "draft"), encoding="utf-8")
    final = render.render(issue, "final")
    (out / f"email_{iso}{sfx}.html").write_text(final, encoding="utf-8")
    archive.publish(out / "site", iso, final.replace('href="site/', 'href="'),
                    {"date_line": issue["date_line"], "label": "Issue 0", "re_line": issue["re_line"]})

    findings = tracker.audit(a.tracker, items) + skipped
    (out / "tracker_audit.txt").write_text("\n".join(findings) + "\n", encoding="utf-8")
    print(f"words: {render.word_count(issue)}; audit findings: {len(findings)}")


if __name__ == "__main__":
    main()
