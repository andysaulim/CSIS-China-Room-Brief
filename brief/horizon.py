"""On the Horizon: one calendar built from three sources.

- the ER tracker (Global Events and Policy Developments tabs)
- the China Daily Brief's "Upcoming" calendar, which carries the dates that
  matter most for U.S.-China relations (elections, deadlines, anniversaries)
- Congress.gov hearings scheduled after the issue date

Each entry gets a type (Deadline, Election, Summit, Hearing, Anniversary,
Meeting), a one-line U.S.-China angle taken from its own source text, and a
relevance score. The next 30 days run in full; later dates run as one line
each, best-scored first. Where two sources give different dates for the same
thing, the draft says so.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

_ANGLE = re.compile(r"\b(China|Chinese|Beijing|Xi|U\.?S\.?|United States|Trump|Taiwan|PLA|CCP)\b")
_GENERIC = {"summit", "meeting", "meetings", "leaders", "leaders'", "annual", "china", "chinese", "economic",
            "forum", "conference", "session", "edition", "global", "world", "national", "approach", "lapse",
            "elections", "election", "anniversary", "united", "states", "international", "the", "and"}
_MONTH = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _sentences(text: str) -> list[str]:
    text = re.sub(r"\s*—\s*", ", ", text or "")
    return [s.strip() for s in re.split(r"(?<=\.)\s+(?=[A-Z\"'])", text) if s.strip()]


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _trim(s: str, words: int = 30) -> str:
    w = s.split()
    if len(w) <= words:
        return s.rstrip(";")
    cut = " ".join(w[:words])
    m = re.search(r"^(.*[,;])\s", cut)
    return (m.group(1).rstrip(",;") if m and len(m.group(1).split()) > 12 else cut) + "."


def angle_from(desc: str) -> str:
    """The first sentence of the source's own description that bears on U.S.-China."""
    body = re.split(r"\s+-\s+|\s+—\s+", desc or "", maxsplit=1)
    text = body[1] if len(body) > 1 and len(body[0]) < 60 else (desc or "")
    sents = _sentences(text)
    for s in sents:                      # a line about Xi, Taiwan or the bilateral first
        if re.search(r"\bXi\b|Taiwan|Trump-Xi|U\.?S\.?-China", s):
            clause = next((c for c in re.split(r";\s+", s) if re.search(r"\bXi\b|Taiwan|China", c)), s)
            return _cap(_trim(clause.rstrip(".") + "."))
    for s in sents:
        if _ANGLE.search(s):
            clause = next((c for c in re.split(r";\s+", s) if _ANGLE.search(c)), s)
            return _cap(_trim(clause.rstrip(".") + "."))
    return _cap(_trim(sents[0])) if sents else ""


def kind(title: str, text: str) -> str:
    t = f"{title} {text}".lower()
    if re.search(r"expir|lapse|deadline|truce", t):
        return "Deadline"
    if "election" in t:
        return "Election"
    if "anniversary" in t:
        return "Anniversary"
    if re.search(r"summit|leaders'|leaders’|g20|g7|apec|asean", t):
        return "Summit"
    if re.search(r"\b(meetings?|forum|conference|dialogue|expo|session)\b", t):
        return "Meeting"
    return "Event"


_SCORE = {"Deadline": 5, "Election": 4, "Hearing": 3, "Summit": 3, "Anniversary": 2, "Meeting": 1, "Event": 1}


def score(e: dict) -> int:
    s = _SCORE.get(e["type"], 1)
    if re.search(r"\b(Xi|Trump|Taiwan|U\.S\.-China|US-China|South China Sea)\b", f'{e["title"]} {e.get("angle", "")}'):
        s += 2
    return s


def _keys(title: str) -> set[str]:
    toks = re.findall(r"[A-Za-z0-9']+", title)
    return {t.lower() for t in toks if (t.isupper() and len(t) >= 3) or (t[:1].isupper() and len(t) >= 4)} - _GENERIC


# ---------- sources ----------

def from_tracker(items, issue_date: date, days: int = 150) -> list[dict]:
    end = issue_date + timedelta(days=days)
    out = []
    for i in items:
        if i.tab not in ("Global Events", "Policy Developments") or i.end < issue_date or i.start > end:
            continue
        where = re.split(r"\s+-\s+|\s+—\s+|\s+\(", i.description or "", maxsplit=1)[0].strip()
        if len(where) > 40 or "," not in where:
            where = ""
        out.append({"start": i.start, "end": i.end, "precision": i.precision, "title": i.name, "where": where,
                    "angle": angle_from(i.description), "url": i.link, "source": "tracker",
                    "type": kind(i.name, i.description)})
    return out


def parse_daily_upcoming(html: str, issue_date: date) -> list[dict]:
    """Rows from the daily brief's Upcoming calendar."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    out, section = [], ""
    for el in soup.find_all("table"):
        if "sec-bar" in (el.get("class") or []):
            section = el.get_text(" ", strip=True)
            continue
        if "Upcoming" not in section or "border-bottom:1px solid #E8E8E8" not in (el.get("style") or ""):
            continue
        tr = el.find("tr")
        tds = tr.find_all("td", recursive=False) if tr else []
        if len(tds) < 2:
            continue
        m = re.match(r"([A-Za-z]{3})\w*\s*\|?\s*(\d{1,2})", tds[0].get_text(" | ", strip=True))
        if not m or m.group(1).lower() not in _MONTH:
            continue
        mon, day = _MONTH[m.group(1).lower()], int(m.group(2))
        year = issue_date.year + (1 if mon < issue_date.month - 1 else 0)
        try:
            d = date(year, mon, day)
        except ValueError:
            continue
        divs = [x.get_text(" ", strip=True) for x in tds[1].find_all("div", recursive=False)]
        title, detail = (divs + ["", ""])[:2]
        typ = kind(title, detail)
        where = ""
        if "," in title:
            head, tail = [p.strip() for p in title.rsplit(",", 1)]
            if not re.search(r"\d|anniversary|session|meeting", tail, re.I):   # a place, not a qualifier
                title, where = head, tail
        out.append({"start": d, "end": d, "precision": "day", "title": title, "where": where,
                    "angle": _cap(_trim(_sentences(detail)[0])) if detail else "", "url": "",
                    "source": "China Daily Brief", "type": typ})
    return out


def from_docket(dk: dict, issue_date: date) -> list[dict]:
    out = []
    for h in (dk or {}).get("hearings", []):
        d = date.fromisoformat(h["date"])
        if d >= issue_date:
            out.append({"start": d, "end": d, "precision": "day", "title": h["title"], "where": "",
                        "angle": f'{h["chamber"]}: {h["committee"]}', "url": h.get("url", ""),
                        "source": "Congress.gov", "type": "Hearing"})
    return out


# ---------- merge and lay out ----------

def merge(entries: list[dict]) -> tuple[list[dict], list[str]]:
    """Fold duplicates (same thing, overlapping dates) and flag date conflicts."""
    merged, notes = [], []
    for e in sorted(entries, key=lambda x: (x["start"], x["source"] != "tracker")):
        k = _keys(e["title"])
        twin = next((m for m in merged if k & _keys(m["title"])
                     and abs((m["start"] - e["start"]).days) <= 2), None)
        if twin:
            if e["source"] == "China Daily Brief" and e.get("angle"):
                twin["angle"] = e["angle"]          # the daily's line is written for this beat
            twin["where"] = twin["where"] or e["where"]
            if e.get("url") and not twin.get("url"):
                twin["url"] = e["url"]
            continue
        merged.append(dict(e))
    for a in merged:
        for b in merged:
            if a is not b and a["source"] != b["source"] and _keys(a["title"]) & _keys(b["title"]) \
                    and abs((a["start"] - b["start"]).days) > 2 and a["start"] < b["start"]:
                notes.append(f'Dates disagree: "{a["title"]}" {a["start"]:%B %-d} ({a["source"]}) vs '
                             f'"{b["title"]}" {b["start"]:%B %-d, %Y} ({b["source"]}). Check before send.')
    for e in merged:
        e["score"] = score(e)
    return merged, notes


def _chip(e) -> tuple[str, str]:
    s, t = e["start"], e["end"]
    if e["precision"] == "month":
        return s.strftime("%B %Y"), "TBC"
    if s == t:
        return s.strftime("%B %Y"), str(s.day)
    if s.month == t.month:
        return s.strftime("%B %Y"), f"{s.day}–{t.day}"
    return s.strftime("%B %Y"), f"{s.day}–{t.strftime('%b')} {t.day}"


GLANCE_DAYS = 7


def glance(entries: list[dict], issue_date: date, days: int = GLANCE_DAYS) -> list[dict]:
    """Calendar entries for the two weeks after the issue date, this week first,
    best first within each. The following week is there to fill Week at a
    Glance when this week's calendar is thin."""
    merged, _ = merge(entries)
    week_end, far_end = issue_date + timedelta(days=days), issue_date + timedelta(days=2 * days)
    out = []
    for e in merged:
        if e["end"] > issue_date and e["start"] <= far_end:
            out.append({**e, "window": "this week" if e["start"] <= week_end else "following week"})
    return sorted(out, key=lambda e: (e["window"] != "this week", -e["score"], e["start"]))


def build(entries: list[dict], issue_date: date, near_days: int = 30, far_cap: int = 6,
          skip_days: int = GLANCE_DAYS, exclude: set | None = None) -> dict:
    """On the Horizon picks up where Week at a Glance stops (day skip_days + 1),
    and leaves out anything Week at a Glance already ran (exclude, by title)."""
    merged, notes = merge(entries)
    merged = [e for e in merged if e["title"] not in (exclude or set())]
    cutoff = issue_date + timedelta(days=near_days)
    near = [e for e in merged if e["start"] > issue_date + timedelta(days=skip_days) and e["start"] <= cutoff]
    far = [e for e in merged if cutoff < e["start"] <= issue_date + timedelta(days=90)]
    far = sorted(sorted(far, key=lambda e: -e["score"])[:far_cap], key=lambda e: e["start"])

    def row(e):
        group, day = _chip(e)
        return {"group": group, "day": day, "headline": e["title"], "type": e["type"],
                "where": e["where"], "angle": e["angle"], "url": e.get("url", ""), "source": e["source"]}

    return {"near": [row(e) for e in near], "far": [row(e) for e in far], "notes": notes}
