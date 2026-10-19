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
        if self.precision == "tbd":
            return "TBD"
        if self.precision == "month":
            lab = self.start.strftime("%b %Y")
            return lab + " (TBC)" if self.tentative else lab
        if self.start == self.end:
            return f"{self.start.strftime('%b')} {self.start.day}"
        if self.start.month == self.end.month:
            return f"{self.start.strftime('%b')} {self.start.day}–{self.end.day}"
        return (f"{self.start.strftime('%b')} {self.start.day}–"
                f"{self.end.strftime('%b')} {self.end.day}")


TBD = date(9999, 12, 31)    # an undated item: sorts after everything dated
_TBD = re.compile(r"^\s*(tbd|tbc|tba|date tbd|to be determined|to be confirmed|n/?a)?\s*$", re.I)


def parse_date(val):
    """Cell value -> (start, end, precision, tentative) or None. Blank or "TBD" gives precision "tbd"."""
    if val is None or (isinstance(val, str) and _TBD.match(val)):
        return TBD, TBD, "tbd", True
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


_COLS = {   # header keywords -> field; first match wins
    "date": ("date", "when", "deadline"),
    "type": ("type", "category", "kind", "format"),
    "name": ("name", "title", "event", "product", "publication"),
    "desc": ("description", "notes", "detail", "summary", "about"),
    "status": ("status", "stage"),
    "link": ("link", "url", "source", "resource"),
}


def tab_role(name: str) -> str | None:
    """Which section a tab feeds, by its name, so renamed or added tabs still load."""
    n = name.lower()
    if "master" in n or "readme" in n or "instruction" in n:
        return None
    if "publish" in n or "publication" in n or "released" in n:
        return "published"
    if "csis" in n or "activit" in n or "in the works" in n or "upcoming" in n:
        return "works"
    if "global" in n or "event" in n or "policy" in n or "horizon" in n or "calendar" in n:
        return "horizon"
    return None


def _header_map(ws) -> tuple[int, dict]:
    """(header row number, field -> column index), falling back to the original layout."""
    for r, row in enumerate(ws.iter_rows(min_row=1, max_row=5, values_only=True), start=1):
        cells = [str(c).strip().lower() if c is not None else "" for c in row]
        if sum(bool(c) for c in cells) < 3:
            continue
        found = {}
        for f, words in _COLS.items():
            for i, c in enumerate(cells):
                if i not in found.values() and any(w in c for w in words):
                    found[f] = i
                    break
        if "date" in found and "name" in found:
            return r, found
    return 1, {"date": 0, "type": 1, "name": 2, "desc": 3, "status": 4, "link": 5}


def describe(path: str) -> list[str]:
    """One line per tab: its role, header row and columns, so a new sheet layout shows in the run log."""
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    out = []
    for name in wb.sheetnames:
        ws = wb[name]
        hr, cols = _header_map(ws)
        heads = [str(c).strip() for c in next(ws.iter_rows(min_row=hr, max_row=hr, values_only=True), ()) if c]
        out.append(f"{name} [{tab_role(name) or 'skipped'}], {ws.max_row - hr} rows, columns: {', '.join(heads[:10])}")
    return out


def load(path: str, role: str | None = None):
    """Return (items, skipped). skipped lists rows whose date cannot be read.
    role forces every tab to one section, for a sheet that feeds only one."""
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    items, skipped, seen = [], [], set()
    for tab in wb.sheetnames:
        if role:   # a one-section sheet: every working tab feeds that section
            tab_kind = None if re.search(r"master|readme|instruction|archive", tab, re.I) else role
        else:
            tab_kind = tab_role(tab)
        if not tab_kind:
            continue
        key_tab = f"{role}: {tab}" if role else tab     # two sheets can both have a "Sheet1"
        SOURCE_TABS[key_tab] = tab_kind
        ws = wb[tab]
        hr, cols = _header_map(ws)
        for r, row in enumerate(ws.iter_rows(min_row=hr + 1, values_only=True), start=hr + 1):
            row = list(row)
            get = lambda f: row[cols[f]] if f in cols and cols[f] < len(row) else None
            raw_date, typ, name, desc, status, link = (get(f) for f in ("date", "type", "name", "desc", "status", "link"))
            if not name:
                continue
            key = (str(name).strip().lower())
            if key in seen:
                continue
            seen.add(key)
            parsed = parse_date(raw_date)
            issues = []
            if parsed is None:
                skipped.append(f"{key_tab} row {r} ({name}): unreadable date {raw_date!r}")
                continue
            if isinstance(raw_date, str) and parsed[2] != "tbd":
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
            items.append(Item(key_tab, r, start, end, prec, tent, str(typ or ""),
                              str(name).strip().replace(" \u2014 ", ": "), str(desc or "").strip(),
                              str(status or "").strip(), str(link or "").strip(), issues))
    return items, skipped


def add_events(items, events: list[dict]) -> int:
    """Fold csis.org China events into In the Works, skipping any the tracker already has."""
    have = {re.sub(r"\W+", " ", i.name.lower()).strip() for i in items}
    tab = "CSIS events (csis.org)"
    SOURCE_TABS.setdefault(tab, "works")
    n = 0
    for e in events:
        if re.sub(r"\W+", " ", e["title"].lower()).strip() in have:
            continue
        items.append(Item(tab, 0, e["date"], e["date"], "day", False, "Event", e["title"], "", "", e["url"], []))
        n += 1
    return n


def published(items, start: date, end: date) -> list[dict]:
    """Rows from a publications tab dated in the week, shaped as Research Roundup sources."""
    return [{"institution": "CSIS", "title": i.name, "url": i.link, "date": i.start.isoformat(),
             "summary": i.description, "authors": []}
            for i in items if SOURCE_TABS.get(i.tab) == "published" and start <= i.start <= end and i.link]


def on_the_horizon(items, issue_date: date, weeks: int = 7, limit: int = 6):
    """Global events and policy deadlines from the issue date forward."""
    horizon = date.fromordinal(issue_date.toordinal() + weeks * 7)
    out = [i for i in items if SOURCE_TABS.get(i.tab) == "horizon"
           and i.end >= issue_date and i.start <= horizon]
    return sorted(out, key=lambda i: i.start)[:limit]


def week_ahead(items, issue_date: date):
    """Tracker rows that fall in the seven days after the issue: candidates for
    the human-written Week at a Glance."""
    end = date.fromordinal(issue_date.toordinal() + 7)
    return sorted([i for i in items if i.end >= issue_date and i.start <= end],
                  key=lambda i: i.start)


def in_the_works(items, issue_date: date, limit: int = 5):
    """The next items chronologically; a month-only date sorts after the dated items
    in its month, and TBD items come last."""
    key = lambda i: (i.start.year, i.start.month, i.precision != "day", i.start.day)
    out = [i for i in items if SOURCE_TABS.get(i.tab) == "works" and i.end >= issue_date]
    # The tracker's own rows come first; csis.org events only fill open slots.
    sheet = sorted([i for i in out if i.row], key=key)[:limit]
    web = sorted([i for i in out if not i.row], key=key)[:limit - len(sheet)]
    return sorted(sheet + web, key=key)


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
