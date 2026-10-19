"""Checks run on every draft. They go to the run log and the issue JSON, not
the email, so nothing has to be deleted before send. They flag; they never
rewrite."""

from __future__ import annotations

import re
from datetime import date

BANNED = ["underscore", "landscape", "navigate", "robust", "pivotal", "key takeaway", "it remains to be seen",
          "it is important to note", "holistic", "stakeholders", "multifaceted", "delve", "tapestry",
          "in a move", "amid growing", "sends a signal"]
_AP_DATE = re.compile(r"\b(Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\.\s+\d")


def check(copy: dict, window: tuple[date, date]) -> list[str]:
    """Plain-language findings, most important first."""
    out = []
    lo = window[0].isoformat()
    hill = copy.get("heard_on_the_hill", [])
    impact = copy.get("csis_impact") or {}
    research, engaged = impact.get("research", []), impact.get("engagements", [])

    if not hill:
        out.append("Heard on the Hill is empty: no approved-source items this week.")
    if not research and not engaged:
        out.append("CSIS Impact is empty: no China research found on csis.org and no form submissions in the week.")
    for it in hill + research + engaged:
        if not it.get("url") and it not in engaged:     # form submissions often carry no link
            out.append(f'No link: "{it.get("headline") or it.get("title") or it.get("line", "")[:60]}".')
        elif "news.google.com" in it["url"]:
            out.append(f'Google News redirect instead of the publisher link: "{it.get("headline") or it.get("title")}".')
        if it.get("iso", "9") < lo:
            out.append(f'Dated {it["iso"]}, before the week covered: "{it.get("headline") or it.get("title")}".')
    for it in research:
        if not it.get("line"):
            out.append(f'CSIS Impact: no line for "{it["title"]}" (page could not be read). Add one or cut it.')
        elif len(it["line"].split()) > 25:
            out.append(f'CSIS Impact line over 25 words: "{it["title"]}".')
    for it in engaged:
        if len(it.get("line", "").split()) > 25:
            out.append(f'CSIS Impact engagement line over 25 words: "{it["line"][:60]}".')

    # prose: the brief's own words only (CSIS titles and approved topics are quoted as they stand)
    text = " ".join([x.get("headline", "") + " " + x.get("body", "") for x in hill]
                    + [x.get("line", "") for x in research + engaged])
    for w in BANNED:
        if re.search(rf"\b{re.escape(w)}\b", text, re.I):
            out.append(f'Word to replace: "{w}".')
    if "—" in text:
        out.append("Em dash in the copy.")
    if _AP_DATE.search(text):
        out.append("Abbreviated month in the copy.")
    return out
