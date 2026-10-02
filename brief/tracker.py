"""Read the ER-maintained US-China tracker workbook.

Feeds two sections: In the Works @ CSIS (the CSIS Activities tab) and
On the Horizon (Global Events + Policy Developments). The Master View tab is
skipped: it is a Google Sheets VSTACK formula whose cached values go stale once
the file is saved as .xlsx, and its ranges already miss rows (see audit()).
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date, datetime

SOURCE_TABS = {
    "CSIS Activities": "works",
    "Global Events": "horizon",
    "Policy Developments": "horizon",
}

_RANGE = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*-\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$")
_DAY = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$")
_MONTH = re.compile(r"^\s*(\d{1,2})/(\d{4})\s*(TBC|TBD)?\s*$", re.I)


@dataclass
class Item:
    tab: str
    row: int
    start: date
    end: date
    precision: str          # "day" or "month"
    tentative: bool
    type: str
    name: str
    description: str
    status: str
    link: str
    issues: list = field(default_factory=list)

    @property
    def date_label(self) -> str:
        if self.precision == "month":
            lab = self.start.strftime("%b %Y")
            return lab + " (TBC)" if self.tentative else lab
        if self.start == self.end:
            return f"{self.start.strftime('%b')} {self.start.day}"
        if self.start.month == self.end.month:
            return f"{self.start.strftime('%b')} {self.start.day}–{self.end.day}"
        return (f"{self.start.strftime('%b')} {self.start.day}–"
                f"{self.end.strftime('%b')} {self.end.day}")


def parse_date(val):
    """Cell value -> (start, end, precision, tentative) or None."""
    if isinstance(val, datetime):
        d = val.date()
        return d, d, "day", False
    if isinstance(val, date):
        return val, val, "day", False
    if not isinstance(val, str) or not val.strip():
        return None
    if m := _RANGE.match(val):
        a, b, c, d, e, f = map(int, m.groups())
        return date(c, a, b), date(f, d, e), "day", False
    if m := _DAY.match(val):
        a, b, c = map(int, m.groups())
        d = date(c, a, b)
        return d, d, "day", False
    if m := _MONTH.match(val):
        mo, yr = int(m.group(1)), int(m.group(2))
        last = calendar.monthrange(yr, mo)[1]
        return date(yr, mo, 1), date(yr, mo, last), "month", bool(m.group(3))
    return None


def load(path: str):
    """Return (items, skipped). skipped lists rows whose date cannot be read."""
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    items, skipped, seen = [], [], set()
    for tab in SOURCE_TABS:
        if tab not in wb.sheetnames:
            continue
        ws = wb[tab]
        for r, row in enumerate(ws.iter_rows(min_row=2, max_col=6, values_only=True), start=2):
            raw_date, typ, name, desc, status, link = (list(row) + [None] * 6)[:6]
            if not name:
                continue
            key = (str(name).strip().lower())
            if key in seen:
                continue
            seen.add(key)
            parsed = parse_date(raw_date)
            issues = []
            if parsed is None:
                skipped.append(f"{tab} row {r} ({name}): unreadable date {raw_date!r}")
                continue
            if isinstance(raw_date, str):
                issues.append("date typed as text; sorts and filters as text in Sheets")
            if not typ:
                issues.append("Type is blank")
            if not desc:
                issues.append("Description is blank")
            if not link:
                issues.append("no Source/Resource link")
            start, end, prec, tent = parsed
            if "\u2014" in str(name):
                issues.append("em-dash in Name; shown as a colon in the brief")
            items.append(Item(tab, r, start, end, prec, tent, str(typ or ""),
                              str(name).strip().replace(" \u2014 ", ": "), str(desc or "").strip(),
                              str(status or "").strip(), str(link or "").strip(), issues))
    return items, skipped


def on_the_horizon(items, issue_date: date, weeks: int = 7, limit: int = 6):
    """Global events and policy deadlines from the issue date forward."""
    horizon = date.fromordinal(issue_date.toordinal() + weeks * 7)
    out = [i for i in items if SOURCE_TABS[i.tab] == "horizon"
           and i.end >= issue_date and i.start <= horizon]
    return sorted(out, key=lambda i: i.start)[:limit]


def week_ahead(items, issue_date: date):
    """Tracker rows that fall in the seven days after the issue: candidates for
    the human-written Week at a Glance."""
    end = date.fromordinal(issue_date.toordinal() + 7)
    return sorted([i for i in items if i.end >= issue_date and i.start <= end],
                  key=lambda i: i.start)


def in_the_works(items, issue_date: date, limit: int = 4):
    """CSIS products not yet out, soonest first; a month-only (TBC) date sorts
    after the dated items in its month."""
    out = [i for i in items if SOURCE_TABS[i.tab] == "works" and i.end >= issue_date]
    return sorted(out, key=lambda i: (i.start.year, i.start.month,
                                      i.precision != "day", i.start.day))[:limit]


def audit(path: str, items) -> list[str]:
    """Data-quality findings a human should fix in the sheet itself."""
    import openpyxl
    findings = []
    wb = openpyxl.load_workbook(path)  # formulas, not values
    if "Master View" in wb.sheetnames:
        a2 = wb["Master View"]["A2"].value or ""
        if "Global Events'!A4" in str(a2):
            findings.append("Master View: VSTACK reads 'Global Events'!A4:G1002, so rows 2-3 "
                            "(Oct 12 IMF/World Bank, Oct 13 Bloomberg NEF) never reach the "
                            "master list. Start the range at A2.")
        if "CSIS Engagements'!A3" in str(a2):
            findings.append("Master View: VSTACK reads 'CSIS Engagements'!A3, a tab name not in "
                            "the workbook (it is 'CSIS Activities'), starting one row late, so "
                            "the first activity row would be dropped even if the name resolved.")
        if "__xludf.DUMMYFUNCTION" in str(a2):
            findings.append("Workbook is an .xlsx copy of a Google Sheet: the Master View formula "
                            "is frozen at its last cached values. Convert it back to a native "
                            "Google Sheet (File > Save as Google Sheets).")
    if "Policy Developments" in wb.sheetnames:
        g1 = wb["Policy Developments"]["G1"].value
        if g1 and g1 != "Policy Developments":
            findings.append(f"Policy Developments: column G header reads {g1!r}.")
    for i in items:
        for msg in i.issues:
            findings.append(f"{i.tab} row {i.row} ({i.name}): {msg}")
    return findings
