"""Assemble the issue dict that render.py takes, from written copy, the
tracker and the draft-only candidate lists. Shared by build_sample.py and
weekly.py so the sample and live runs build issues the same way."""

from __future__ import annotations

import os
import re
from datetime import date, timedelta

from . import tracker

FOOTER = ("The China Room Brief is compiled by CSIS External Relations. Look-back items draw on the "
          "CSIS China Daily Brief; calendar items come from the China Room editorial calendar.")
CONTACT = {"name": "Nina Prieur", "title": "Director of Strategic Communications, External Relations",
           "email": "nprieur@csis.org"}


def label(d: date) -> str:
    return f"{d.strftime('%b')} {d.day}"


def _chip(i):
    if i.precision == "month":
        return i.start.strftime("%b").upper(), "TBC" if i.tentative else ""
    day = str(i.start.day) if i.start == i.end else f"{i.start.day}–{i.end.day}"
    return i.start.strftime("%b").upper(), day


def _where(desc: str) -> str:
    cuts = [desc.find(sep) for sep in (" — ", " - ", " (") if sep in desc]
    return desc[:min(cuts)].strip() if cuts else desc[:90]


def _program(i) -> str:
    m = re.match(r"^([A-Z][A-Z/]{1,15})\b", i.description or "")
    return " · ".join(x for x in ((m.group(1) if m else ""), i.type) if x)


def calendars(items, issue_date: date):
    works = [{"month": _chip(i)[0], "day": _chip(i)[1], "headline": i.name, "kind": _program(i),
              "detail": i.description, "url": i.link}
             for i in tracker.in_the_works(items, issue_date, limit=5)]
    horizon = [{"month": _chip(i)[0], "day": _chip(i)[1], "headline": i.name,
                "kind": _where(i.description), "detail": "", "url": i.link}
               for i in tracker.on_the_horizon(items, issue_date)]
    return works, horizon


def assemble(copy: dict, tracker_items, issue_date: date, back: tuple[date, date], *,
             issue_label: str, banner_src: str = "", candidates: dict | None = None,
             research_note: str = "", web_base: str | None = None) -> dict:
    candidates = candidates or {}
    web_base = (os.environ.get("CHINA_ROOM_WEB_BASE", "") if web_base is None else web_base).rstrip("/")
    iso = issue_date.isoformat()
    works, horizon = calendars(tracker_items, issue_date)
    ahead_start = issue_date + timedelta(days=(7 - issue_date.weekday()) % 7 or 7)
    return {
        "date_line": f"{issue_date.strftime('%A, %B')} {issue_date.day}, {issue_date.year}",
        "issue_label": issue_label,
        "draft_for": "Nina Prieur · Thursday noon",
        "calendar_url": os.environ.get("CHINA_ROOM_CALENDAR_URL", ""),
        "web_url": f"{web_base}/{iso}.html" if web_base else "",
        "archive_url": f"{web_base}/archive.html" if web_base else "",
        "banner_src": banner_src,
        "re_line": copy.get("re_line", ""),
        "editors_note": copy.get("editors_note", ""),
        "back_window": f"{label(back[0])} to {label(back[1])}",
        "ahead_window": f"{label(ahead_start)} onward",
        "week_at_a_glance": {
            "items": copy.get("week_at_a_glance", []),
            "spec": "Draft above. Rewrite or swap from the candidates below.",
            "candidates": candidates.get("glance", []),
        },
        "heard_on_the_hill": {
            "items": copy.get("heard_on_the_hill", []),
            "spec": "Draft above, from the daily brief's Congress items. Add hearings and floor action it missed.",
            "candidates": candidates.get("hill", []),
        },
        "in_the_news": {"items": copy.get("in_the_news", []),
                        "dek": "Top five China stories of the week in priority outlets"},
        "research_roundup": {
            "items": copy.get("research_roundup", []),
            "spec": "Check each item on its page before send.",
            "gap": research_note,
        },
        "in_the_works": {"items": works},
        "on_the_horizon": {"items": horizon},
        "contact": copy.get("contact", CONTACT),
        "footer": FOOTER,
    }
