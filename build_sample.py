"""Render a China Room Engagement Brief from saved copy, without collecting anything.

    python build_sample.py --tracker data/CSIS_US_China_Tracker.xlsx \
        [--copy samples/engagement_sample.json] [--issue-date 2026-10-20]

Writes out/sample_draft_<date>.html and out/sample_final_<date>.html. Use it
to check the layout after a template change; weekly.py is the live run.
"""

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from brief import render, tracker
from brief.issue import assemble


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracker", required=True, help="an .xlsx of the calendar sheet(s)")
    ap.add_argument("--copy", default="samples/engagement_sample.json")
    ap.add_argument("--issue-date", default="2026-10-20")
    ap.add_argument("--banner", default="../assets/banner_china_room.png")
    ap.add_argument("--calendar-url", default="")
    ap.add_argument("--horizon-url", default="")
    a = ap.parse_args()

    d = date.fromisoformat(a.issue_date)
    copy = json.loads(Path(a.copy).read_text(encoding="utf-8"))
    items, _ = tracker.load(a.tracker)
    out = Path("out")
    out.mkdir(exist_ok=True)
    for mode in ("draft", "final"):
        issue = assemble(json.loads(json.dumps(copy)), items, d, (d - timedelta(days=7), d - timedelta(days=1)),
                         issue_label="Sample", banner_src=a.banner)
        issue["calendar_url"], issue["horizon_url"] = a.calendar_url, a.horizon_url
        f = out / f"sample_{mode}_{d.isoformat()}.html"
        f.write_text(render.render(issue, mode), encoding="utf-8")
        print(f"{f}: {render.word_count(issue)} words")


if __name__ == "__main__":
    main()
