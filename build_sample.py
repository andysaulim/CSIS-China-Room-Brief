"""Build the sample Monday-noon draft for the Oct 6, 2026 issue.

    python build_sample.py --tracker data/CSIS_US_China_Tracker.xlsx \
        --ledger ../andysaulim/daily-china-digest/published_ledger.json --out out/

Everything in the sample comes from two real inputs: the China Daily Brief
ledger (Sep 28 to Oct 2, the days that exist as of this build) and the ER
tracker. In the News picks are hand-chosen by URL from the ledger to show the
target shape; in production Claude makes that pick.
"""

import argparse
import os
from datetime import date
from pathlib import Path

from brief import daily_feed, render, tracker

ISSUE = date(2026, 10, 6)            # Tuesday send
BACK = (date(2026, 9, 28), date(2026, 10, 4))
# The tracker's share link is not kept in this public repository.
CALENDAR_URL = os.environ.get("CHINA_ROOM_CALENDAR_URL", "")

# Ledger headlines from Sep 30 onward arrive in Title Case; the brief runs
# sentence case. Same words, case only.
CASE = {
    "PBOC Unveils Stimulus Package: Mortgage Subsidy, PSL Cut, 1.2 Trillion Yuan Reverse Repo":
        "PBOC unveils stimulus package: mortgage subsidy, PSL cut, 1.2 trillion yuan reverse repo",
    "Suspected Chinese Hackers Impersonated US AI Insiders":
        "Suspected Chinese hackers impersonated US AI insiders",
    "US Officials See Chinese Invasion of Taiwan Unlikely Before 2028":
        "US officials see Chinese invasion of Taiwan unlikely before 2028",
}

# (ledger URL fragment, tag override, body). Body cites only other ledger rows.
NEWS = [
    ("nytimes.com/2026/09", None,
     "The week's most-covered China story among priority outlets: the Wall Street Journal "
     "(Sep 28), AP (Sep 29) and the Guardian (Sep 30) followed, with the White House denying any offer."),
    ("cnn.com", "cnn-tariff",
     "Reuters (Sep 28): Beijing's farm-goods relief list leaves out soybeans."),
    ("pboc-unveils", None,
     "CNBC (Sep 30): the official factory PMI rose to 50.1, ending two months of contraction."),
    ("resolutely", None,
     "WSJ (Oct 1): behind the summit pageantry, Xi's eyes were on Taiwan."),
    ("hackers-impersonated-us-ai", None,
     "FT (Oct 1): Britain's MI5 accuses a Chinese institute of spying on AI research."),
    ("invasion", None, ""),
]


def pick(entries, frag, used):
    for x in entries:
        if x["url"] in used:
            continue
        hay = (x["url"] + " " + x["headline"]).lower()
        if frag.lower() in hay or frag.replace("-", " ").lower() in hay:
            used.add(x["url"])
            return x
    raise SystemExit(f"no ledger match for {frag!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracker", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--out", default="out")
    ap.add_argument("--banner", default="../assets/banner_china_room.png",
                    help="banner image URL; in a sent email this must be a public https URL "
                         "(Pardot file host or raw.githubusercontent). Pass '' for the text masthead.")
    a = ap.parse_args()

    items, skipped = tracker.load(a.tracker)
    ledger = daily_feed.in_window(daily_feed.load_ledger(a.ledger), *BACK)
    pri = daily_feed.priority_items(ledger)

    # In the News
    used, news = set(), []
    lookup = {
        "cnn-tariff": lambda: next(x for x in pri if "tariff-cut lists" in x["headline"]),
    }
    for frag, special, body in NEWS:
        x = lookup[special]() if special else pick(pri, frag, used)
        d = date.fromisoformat(x["date"])
        news.append({"tag": f'{x["outlet"]} &middot; {d.strftime("%b")} {d.day}',
                     "headline": CASE.get(x["headline"], x["headline"]),
                     "url": x["url"], "body": body})

    def cand(x):
        d = date.fromisoformat(x["date"])
        return {"text": x["headline"], "url": x["url"], "source": x["outlet"],
                "date_label": f'{d.strftime("%b")} {d.day}'}

    hill = [cand(x) for x in daily_feed.hill_candidates(ledger)]
    ahead_news = [cand(x) for x in daily_feed.forward_candidates(ledger)[:4]]
    ahead_cal = [{"text": i.name, "url": i.link, "date_label": i.date_label,
                  "source": "ER tracker"} for i in tracker.week_ahead(items, ISSUE)]

    def chip(i):
        if i.precision == "month":
            return i.start.strftime("%b").upper(), "TBC" if i.tentative else ""
        day = str(i.start.day) if i.start == i.end else f"{i.start.day}–{i.end.day}"
        return i.start.strftime("%b").upper(), day

    def where(desc):
        cuts = [desc.find(sep) for sep in (" \u2014 ", " - ", " (") if sep in desc]
        return desc[:min(cuts)].strip() if cuts else desc[:90]

    works = []
    for i in tracker.in_the_works(items, ISSUE, limit=5):
        m, d = chip(i)
        works.append({"month": m, "day": d, "headline": i.name, "detail": i.description,
                      "url": i.link})
    horizon = []
    for i in tracker.on_the_horizon(items, ISSUE):
        m, d = chip(i)
        horizon.append({"month": m, "day": d, "headline": i.name, "detail": where(i.description),
                        "url": i.link})

    issue = {
        "date_line": "Tuesday, October 6, 2026",
        "issue_label": "Issue 0 · sample",
        "draft_for": "Nina · Monday noon",
        "banner_src": a.banner,
        "calendar_url": CALENDAR_URL,
        "re_line": "Perdue's arms-offer disclosure · $60B tariff lists · PBOC stimulus "
                   "· Xi's National Day Taiwan line · AI-insider hacking",
        "back_window": "Sep 28 to Oct 4 · sample uses China Daily Brief issues through Oct 2",
        "ahead_window": "Oct 6 onward · from the China Room editorial calendar",
        "week_at_a_glance": {
            "spec": "Three forward-looking items for the week of Oct 6, about 50 words each: "
                    "what happens in US-China relations this week and why it matters.",
            "candidates": ahead_cal + ahead_news,
        },
        "heard_on_the_hill": {
            "spec": "Three to five items, 30 to 40 words each: bills, hearings, letters and "
                    "member statements on China from the past week.",
            "candidates": hill,
        },
        "in_the_news": {"dek": "Lead story is the one the most priority outlets carried",
                        "items": news},
        "research_roundup": {
            "spec": "Two to five think-tank or CRS publications from the past week, one line each.",
            "gap": "No input yet. The China Daily Brief collects 81 think-tank feeds and 18 "
                   "journals but stopped publishing them, so they never reach its archive. "
                   "Fix in the daily repo before the first live issue (README, step 2).",
        },
        "in_the_works": {"items": works},
        "on_the_horizon": {"items": horizon},
        "footer": ("Look-back items come from the CSIS China Daily Brief archive; calendar items "
                   "from the China Room editorial calendar maintained by External Relations. "
                   "<a href='" + CALENDAR_URL + "' style='color:#6B7280;'>Full calendar</a>."),
    }

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "sample_draft_2026-10-06.html").write_text(render.render(issue, "draft"), encoding="utf-8")
    (out / "sample_final_2026-10-06.html").write_text(render.render(issue, "final"), encoding="utf-8")

    findings = tracker.audit(a.tracker, items) + skipped
    (out / "tracker_audit.txt").write_text("\n".join(findings) + "\n", encoding="utf-8")
    print(f"words (final): {render.word_count(issue)}; hill candidates: {len(hill)}; "
          f"glance candidates: {len(ahead_cal) + len(ahead_news)}; audit findings: {len(findings)}")


if __name__ == "__main__":
    main()
