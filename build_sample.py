"""Build Issue 0 (Friday, Oct 2, 2026) from real inputs.

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
from brief.issue import assemble

ISSUE = date(2026, 10, 2)
BACK = (date(2026, 9, 26), date(2026, 10, 2))
WEB_BASE = os.environ.get("CHINA_ROOM_WEB_BASE", "").rstrip("/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracker", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--copy", default="samples/issue0_copy_house.json")
    ap.add_argument("--banner", default="../assets/banner_china_room.png",
                    help="banner URL; a sent email needs a public https URL")
    ap.add_argument("--theme", default="newsroom", choices=["newsroom", "pubs", "briefing"])
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

    iso = ISSUE.isoformat()
    issue = assemble(
        copy, items, ISSUE, BACK, issue_label="Issue 0 (sample)", banner_src=a.banner,
        web_base=WEB_BASE,
        candidates={
            "glance": [{"text": i.name, "url": i.link, "date_label": i.date_label, "source": "tracker"}
                       for i in tracker.week_ahead(items, ISSUE)]
                      + [cand(x) for x in daily_feed.forward_candidates(ledger)[:4]],
            "hill": [cand(x) for x in daily_feed.hill_candidates(ledger)],
        },
        research_note="Found by search; the publication pages could not be opened from the build "
                      "machine. No CRS China product was found dated Sep 26 to Oct 2.")
    if not WEB_BASE:   # local preview: point the links at out/site/
        issue["web_url"], issue["archive_url"] = f"site/{iso}.html", "site/archive.html"

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sfx = a.suffix
    (out / f"draft_{iso}{sfx}.html").write_text(render.render(issue, "draft", a.theme), encoding="utf-8")
    final = render.render(issue, "final", a.theme)
    (out / f"email_{iso}{sfx}.html").write_text(final, encoding="utf-8")
    # Self-contained preview with the banner embedded, for sharing as a file.
    import base64
    png = Path(__file__).parent / "assets" / "banner_china_room.png"
    if a.banner and png.exists():
        data = "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode()
        (out / f"preview_{iso}{sfx}.html").write_text(final.replace(a.banner, data), encoding="utf-8")
    archive.publish(out / "site", iso, final.replace('href="site/', 'href="').replace(
                        a.banner, "../../assets/banner_china_room.png"),
                    {"date_line": issue["date_line"], "label": "Issue 0", "re_line": issue["re_line"]})

    findings = tracker.audit(a.tracker, items) + skipped
    (out / "tracker_audit.txt").write_text("\n".join(findings) + "\n", encoding="utf-8")
    print(f"words: {render.word_count(issue)}; audit findings: {len(findings)}")


if __name__ == "__main__":
    main()
