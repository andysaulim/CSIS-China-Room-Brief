"""CSIS Impact engagements: last week's Google Form submissions.

The form's response sheet (ENGAGEMENTS_URL) has a Timestamp column and one
column per question. Rows stamped inside the week are passed to the draft
with every answered field, and the model writes one line from them.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from . import sheets

_SKIP = re.compile(r"timestamp|email address", re.I)
_WHO = re.compile(r"\b(name|scholar|program|submitted by|staff|who)\b", re.I)
_LINK = re.compile(r"\b(link|url)\b", re.I)


def _when(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(v).strip(), fmt).date()
        except ValueError:
            continue
    return None


def engagements(url: str, start: date, end: date) -> list[dict]:
    if not url:
        return []
    out = []
    for r in sheets.rows(url):
        stamp = next((v for k, v in r.items() if "timestamp" in k.lower()), None)
        d = _when(stamp)
        if not d or not (start <= d <= end):
            continue
        fields = {k: v for k, v in r.items() if not _SKIP.search(k) and str(v).strip()}
        who = next((str(v) for k, v in fields.items() if _WHO.search(k)), "")
        link = next((str(v) for k, v in fields.items() if _LINK.search(k) and str(v).startswith("http")), "")
        out.append({"date": d.isoformat(), "who": who, "url": link, "fields": fields})
    return out
