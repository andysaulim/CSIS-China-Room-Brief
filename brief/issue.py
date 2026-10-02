"""Assemble the issue dict that render.py takes, from written copy, the
tracker and the draft-only candidate lists. Shared by build_sample.py and
weekly.py so the sample and live runs build issues the same way."""

from __future__ import annotations

import os
import re
from datetime import date, timedelta

from . import horizon as hz
from . import tracker

FOOTER = ("The China Room Brief is compiled by CSIS External Relations. Look-back items draw on the "
          "CSIS China Daily Brief; calendar items come from the China Room editorial calendar.")
CONTACT = {"name": "Nina Prieur", "title": "Director of Strategic Communications, External Relations",
           "email": "nprieur@csis.org"}


_US = re.compile(r"\bUS\b(?![$])")
_MONTHS = {"Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April", "Jun": "June",
           "Jul": "July", "Aug": "August", "Sep": "September", "Sept": "September", "Oct": "October",
           "Nov": "November", "Dec": "December"}
_MON = re.compile(r"\b(Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\.?(?=\s+\d)")


def csis_style(obj):
    """CSIS style: "U.S.", never "US"; months written out. Every copy string, not URLs."""
    if isinstance(obj, dict):
        return {k: (v if k in ("url",) else csis_style(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [csis_style(x) for x in obj]
    if isinstance(obj, str):
        out = _MON.sub(lambda m: _MONTHS[m.group(1)], _US.sub("U.S.", obj))
        # day ranges ("October 1-7") take an en dash; ISO dates are left alone
        return re.sub(r"(?<![\d-])(\d{1,2})-(\d{1,2})(?![\d-])", "\\1\u2013\\2", out)
    return obj


def label(d: date) -> str:
    return f"{d.strftime('%B')} {d.day}"


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
    return " ".join(x for x in ((m.group(1) if m else ""), i.type.lower() if m else i.type) if x)


def _short(desc: str) -> str:
    """One line from the tracker's notes: the first clause, program code removed."""
    d = re.sub(r"^[A-Z][A-Z/]{1,15}\s+", "", desc or "").strip()
    d = re.split(r";\s|\.\s+(?=\d|[A-Z])", d, maxsplit=1)[0].rstrip(".")
    return d


def _group(i) -> str:
    g = i.start.strftime("%B %Y")
    return g + ", date to come" if i.precision == "month" else g


_SMALL = {"a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "into", "nor", "of", "on", "or",
          "the", "to", "vs", "with"}


def headline_case(t: str) -> str:
    """Chicago headline case for titles that arrive in sentence case."""
    words = t.split(" ")
    if sum(w[:1].isupper() for w in words if w[:1].isalpha()) > len(words) / 2:
        return t                      # already in headline case
    out = []
    for n, w in enumerate(words):
        bare = w.strip("\"'(“‘")
        if n and n < len(words) - 1 and bare.lower() in _SMALL:
            out.append(w.lower())
        elif bare[:1].islower():
            k = len(w) - len(w.lstrip("\"'(“‘"))
            out.append(w[:k] + w[k:k + 1].upper() + w[k + 1:])
        else:
            out.append(w)
    return " ".join(out)


def calendars(items, issue_date: date):
    works = [{"month": _chip(i)[0], "day": "" if i.precision == "month" else _chip(i)[1], "headline": i.name,
              "kind": _program(i), "group": _group(i), "detail": _short(i.description), "url": i.link}
             for i in tracker.in_the_works(items, issue_date, limit=5)]
    horizon = [{"month": _chip(i)[0], "day": _chip(i)[1], "headline": i.name,
                "kind": _where(i.description), "group": _group(i), "detail": "", "url": i.link}
               for i in tracker.on_the_horizon(items, issue_date)]
    return works, horizon


def assemble(copy: dict, tracker_items, issue_date: date, back: tuple[date, date], *,
             issue_label: str, banner_src: str = "", candidates: dict | None = None,
             research_note: str = "", web_base: str | None = None,
             daily_upcoming: list | None = None) -> dict:
    candidates = candidates or {}
    copy = csis_style(copy)
    for r in copy.get("research_roundup", []):
        r["headline"] = headline_case(r["headline"])
    web_base = (os.environ.get("CHINA_ROOM_WEB_BASE", "") if web_base is None else web_base).rstrip("/")
    iso = issue_date.isoformat()
    works, _ = csis_style(list(calendars(tracker_items, issue_date)))
    hzn = hz.build(hz.from_tracker(tracker_items, issue_date) + (daily_upcoming or [])
                   + hz.from_docket(copy.get("hill_docket") or {}, issue_date), issue_date,
                   exclude={g.get("calendar_title") for g in copy.get("week_at_a_glance", []) if g.get("calendar_title")})
    hzn = csis_style(hzn)
    ahead_start = issue_date + timedelta(days=(7 - issue_date.weekday()) % 7 or 7)
    return {
        "date_line": f"{issue_date.strftime('%A, %B')} {issue_date.day}, {issue_date.year}",
        "issue_label": issue_label,
        "iso": iso,
        "draft_for": "Nina Prieur, Thursday noon",
        "calendar_url": os.environ.get("CHINA_ROOM_CALENDAR_URL", ""),
        "web_url": f"{web_base}/{iso}.html" if web_base else "",
        "archive_url": f"{web_base}/archive.html" if web_base else "",
        "banner_src": banner_src,
        "re_line": copy.get("re_line", ""),
        "editors_note": copy.get("editors_note", ""),
        "by_the_numbers": copy.get("by_the_numbers", []),
        "back_window": f"{label(back[0])} to {label(back[1])}",
        "ahead_window": f"{label(ahead_start)} onward",
        "qa": copy.get("qa", []),
        "week_at_a_glance": {
            "items": copy.get("week_at_a_glance", []),
            "spec": "Drafted from the calendars for the seven days after the issue date. Rewrite or swap from the candidates below.",
            "candidates": candidates.get("glance", []),
        },
        "heard_on_the_hill": {
            "items": copy.get("heard_on_the_hill", []),
            "spec": "Drafted from Congress.gov, committee releases and the daily brief. Add hearings and floor action it missed.",
            "candidates": candidates.get("hill", []),
            "docket": copy.get("hill_docket") or {},
        },
        "in_the_news": {"items": copy.get("in_the_news", []),
                        "dek": "Top five China stories of the week in priority outlets"},
        "research_roundup": {
            "items": copy.get("research_roundup", []),
            "spec": "Check each item on its page before send.",
            "gap": research_note,
        },
        "in_the_works": {"items": works},
        "on_the_horizon": {"items": hzn["near"] + hzn["far"], "near": hzn["near"], "far": hzn["far"],
                           "spec": "Calendar check", "gap": " ".join(hzn["notes"])},
        "contact": copy.get("contact", CONTACT),
        "footer": FOOTER,
    }
