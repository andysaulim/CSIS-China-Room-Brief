"""Checks run on every draft. They go in a box at the top of the draft email so
the reviewer knows where to look first. They flag; they never rewrite."""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlparse

from . import config

TARGET_WORDS = 1000
BANNED = ["underscore", "landscape", "navigate", "robust", "pivotal", "key takeaway", "it remains to be seen",
          "it is important to note", "holistic", "stakeholders", "multifaceted", "delve", "tapestry",
          "in a move", "amid growing", "sends a signal"]
_AP_DATE = re.compile(r"\b(Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\.?\s+\d")
_STOP = {"china", "chinese", "beijing", "u.s.", "trump", "said", "would", "with", "that", "from", "after", "their",
         "this", "will", "have", "over", "about", "into", "says", "week", "reported", "united", "states", "washington",
         "the", "again", "also", "reuters", "bloomberg", "times", "journal", "post", "said", "november", "october",
         "september", "summit", "argues"}
SECTIONS = [("week_at_a_glance", "Week at a Glance"), ("heard_on_the_hill", "Heard on the Hill"),
            ("in_the_news", "In the News"), ("research_roundup", "Research Roundup")]


def _words(it: dict) -> set[str]:
    text = f'{it.get("headline", "")} {it.get("body", "")}'
    toks = re.findall(r"[A-Za-z$][\w$.'-]+", text)
    keep = {t.lower().strip(".'") for t in toks if len(t) > 3 or t[0].isupper() or t[0] == "$"}
    return keep - _STOP


def _sentences(s: str) -> list[str]:
    return [x for x in re.split(r"(?<=[.!?])\s+(?=[A-Z\"“])", s or "") if x.strip()]


def check(copy: dict, window: tuple[date, date], calendar_count: int | None = None) -> list[str]:
    """Plain-language findings, most important first."""
    out = []
    if calendar_count == 0:
        out.append("The ER sheet and the daily brief list nothing for the seven days after the issue date. "
                   "Week at a Glance leans on dates found in news reports; add the week's events to the sheet.")
    news_dated = [it["headline"] for it in copy.get("week_at_a_glance", []) if it.get("from_news")]
    if news_dated:
        out.append("Week at a Glance items dated from news reports, not the calendar (confirm the date): "
                   + "; ".join(f'"{h}"' for h in news_dated) + ".")

    # 1. outlets in In the News
    news = copy.get("in_the_news", [])
    outlets = [n["tag"].split(",")[0] for n in news]
    ranks = {name: rank for rank, name, _ in config.PRIORITY_OUTLETS}
    top = sum(1 for o in outlets if ranks.get(o, 99) <= 2)
    if news:
        out.append(f"In the News outlets: {', '.join(outlets)}. {top} of {len(news)} from NYT, WSJ, "
                   f"Washington Post, Bloomberg or FT.")

    # 2. the same event taking more than one slot
    items = [(title, it) for key, title in SECTIONS for it in copy.get(key, [])]
    for key, title in SECTIONS:
        groups = {}
        for it in copy.get(key, []):
            ev = re.sub(r"\W+", " ", (it.get("event") or "").lower()).strip()
            if ev:
                groups.setdefault(ev, []).append(it["headline"])
        limit = 2 if key == "research_roundup" else 1
        for ev, heads in groups.items():
            if len(heads) > limit:
                out.append(f'{title}: {len(heads)} items on one event ({ev}): ' + "; ".join(f'"{h}"' for h in heads) + ".")
    # backup for unlabeled drafts: heavy word overlap inside a section
    for key, title in SECTIONS:
        its = copy.get(key, [])
        for i, a in enumerate(its):
            for b in its[i + 1:]:
                wa, wb = _words(a), _words(b)
                if wa and wb and len(wa & wb) / min(len(wa), len(wb)) >= 0.4 and not (a.get("event") and b.get("event")):
                    out.append(f'{title}: possible repeat: "{a["headline"]}" and "{b["headline"]}".')

    # 3. links that do not reach the publisher
    redirects, missing = [], []
    for key, title in SECTIONS:
        for it in copy.get(key, []):
            u = it.get("url", "")
            if "news.google.com" in u:
                redirects.append(title)
            elif not u and key != "week_at_a_glance":
                missing.append(f'"{it["headline"]}"')
    if redirects:
        out.append(f"{len(redirects)} link(s) go to a Google News redirect, not the publisher "
                   f"({', '.join(sorted(set(redirects)))}). Replace before send.")
    if missing:
        out.append("No link: " + "; ".join(missing) + ".")

    # 4. Hill items resting on a non-U.S. outlet
    for it in copy.get("heard_on_the_hill", []):
        host = (urlparse(it.get("url", "")).hostname or "").removeprefix("www.")
        if host and not host.endswith(".gov") and not config.outlet_for(host):
            out.append(f'Heard on the Hill cites {host}, not a primary record or priority outlet: "{it["headline"]}".')

    # 5. stale items
    lo, hi = window
    for key, title in SECTIONS[1:]:
        for it in copy.get(key, []):
            iso = it.get("iso", "")
            if iso and iso < lo.isoformat():
                out.append(f'{title}: dated {iso}, before the week covered: "{it["headline"]}".')

    # 6. research that restates its title
    echo = []
    for it in copy.get("research_roundup", []):
        h = set(re.findall(r"\w+", it["headline"].lower()))
        b = set(re.findall(r"\w+", it["body"].lower()))
        if h and len(h & b) / len(h) > 0.7:
            echo.append(it["institution"])
    if echo:
        out.append(f"Research Roundup summaries that mostly repeat the title: {', '.join(echo)}. "
                   f"Rewrite from the piece itself.")

    # 7. prose
    bodies = [it.get("body", "") for _, it in items] + [copy.get("editors_note", "")]
    joined = " ".join(bodies + [it.get("headline", "") for _, it in items])
    for w in BANNED:
        if re.search(rf"\b{re.escape(w)}\b", joined, re.I):
            out.append(f'Word to replace: "{w}".')
    if "—" in joined:
        out.append("Em dash in the copy.")
    if _AP_DATE.search(joined):
        out.append("Abbreviated month in the copy (the renderer spells it out, but check the sentence).")
    heavy = [it["headline"] for _, it in items if len(re.findall(r"\breported\b", it.get("body", ""))) >= 2]
    if heavy:
        out.append(f'"Reported" two or more times in {len(heavy)} item(s), first: "{heavy[0]}".')
    lengths = [len(_sentences(b)) for b in bodies if b]
    if lengths and max(lengths.count(n) for n in set(lengths)) / len(lengths) > 0.75:
        out.append("Most items have the same number of sentences. Vary a few; uniform rhythm reads as machine-made.")
    note, lead = copy.get("editors_note", ""), (news[0] if news else {})
    if note and lead and len(_words({"body": note}) & _words(lead)) / max(1, len(_words({"body": note}))) > 0.5:
        out.append("Editor's note restates the top In the News story.")
    return out
