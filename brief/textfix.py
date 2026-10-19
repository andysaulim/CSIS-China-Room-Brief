"""Tidy the one-line notes that come from Brian's sheets before they print.

- A note ends with a period.
- A run of names takes "and" before the last one ("Seth Jones, Eliot Cohen
  and Michael Studeman"), as in the rest of the brief.
- One through nine are spelled out ("seven other economies").
- Scheduling notes meant for the team ("10/28-29 overlaps with the Plenum",
  "dates TBC") are dropped, and a date the entry already shows in its date
  column is not repeated in the text.
"""

from __future__ import annotations

import re
from datetime import date

_WORDS = "one two three four five six seven eight nine".split()
_NAME = r"[A-Z][\w.'’-]+(?: (?:[A-Z][\w.'’-]+|de|van|von|bin))*"
_NAMES = re.compile(rf"\b({_NAME}(?:, {_NAME})+), ({_NAME})\b")
_SCHEDULING = re.compile(r"\b(overlap\w*|conflicts? with|clash\w*|tentative\w*|tbc|tbd|to be confirmed|"
                         r"dates? (?:not )?(?:set|confirmed|pending)|placeholder|check (?:the )?date|hold the date)\b", re.I)
_MON = "Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"


def _clauses(text: str) -> list[str]:
    return [c for c in re.split(r"(?<=[.;!?])\s+", text or "") if c.strip()]


def _own_dates(start: date, end: date) -> re.Pattern:
    """Ways a note might restate the entry's own date: 11/18, 11/18-19, Nov 18, November 18-19."""
    m, d1, d2 = start.month, start.day, end.day
    mon = start.strftime("%B")
    rng = rf"(?:\s*[-–]\s*{d2})?" if end != start else ""
    return re.compile(rf"\(?\b(?:{m}/{d1}(?:/\d{{2,4}})?{rng}|(?:{mon}|{mon[:3]})\.? {d1}{rng}(?:, \d{{4}})?)\b\)?,?\s*")


def clean(text: str, start: date | None = None, end: date | None = None) -> str:
    keep = [c for c in _clauses(text) if not _SCHEDULING.search(c)]
    out = " ".join(keep).strip()
    if start and end and start.year < 9999:
        out = _own_dates(start, end).sub("", out).strip()
        out = re.sub(r"^[,;:\-–\s]+", "", out)
    out = _NAMES.sub(lambda m: f"{m.group(1)} and {m.group(2)}", out)
    out = re.sub(r"(?<![\d$.,/-])\b([1-9])\b(?![\d%/.,:-]|\s*(?:percent|%|th|st|nd|rd))",
                 lambda m: _WORDS[int(m.group(1)) - 1], out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    if out and out[-1] not in ".!?\"'”’)":
        out += "."
    return out[:1].upper() + out[1:] if out else out
