"""China-related hearings and new legislation from the Congress.gov API (v3).

Heard on the Hill used to see Congress only through news coverage, which
misses most hearings and nearly every bill introduction. This reads the
source: committee meetings (held last week or scheduled ahead) and bills
introduced in the window, kept when the title touches China.

Needs CONGRESS_API_KEY (free, from api.data.gov). Written against the
documented v3 endpoints; first exercised on the Thursday run.
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime, time, timedelta, timezone

import requests

API = "https://api.congress.gov/v3"
CONGRESS = 119
CHINA = re.compile(
    r"\b(China|Chinese|PRC|CCP|Communist Party|Beijing|Taiwan|Hong Kong|Xinjiang|Uyghur|Tibet|"
    r"TikTok|ByteDance|Huawei|SMIC|DJI|BYD|CATL|foreign adversar\w*|South China Sea|Indo-Pacific)\b", re.I)
CHINA_COMMITTEES = re.compile(r"Strategic Competition Between the United States and the Chinese Communist Party", re.I)
BILL_PATH = {"HR": "house-bill", "S": "senate-bill", "HRES": "house-resolution", "SRES": "senate-resolution",
             "HJRES": "house-joint-resolution", "SJRES": "senate-joint-resolution",
             "HCONRES": "house-concurrent-resolution", "SCONRES": "senate-concurrent-resolution"}


def _get(path: str, **params) -> dict | None:
    key = os.environ.get("CONGRESS_API_KEY", "")
    if not key:
        return None
    url = path if path.startswith("http") else f"{API}/{path}"
    try:
        r = requests.get(url, params={"api_key": key, "format": "json", **params}, timeout=30)
        return r.json() if r.ok else None
    except (requests.RequestException, ValueError):
        return None


def _stamp(d: date) -> str:
    return datetime.combine(d, time.min, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _paged(path: str, key: str, frm: date, to: date, cap: int = 1000) -> list[dict]:
    out, offset = [], 0
    while offset < cap:
        data = _get(path, fromDateTime=_stamp(frm), toDateTime=_stamp(to + timedelta(days=1)),
                    limit=250, offset=offset)
        rows = (data or {}).get(key) or []
        out += rows
        if len(rows) < 250:
            break
        offset += 250
    return out


def hearings(start: date, end: date) -> list[dict]:
    """China-related committee meetings dated start..end (held or scheduled).
    The list endpoint filters on update time, so look back far enough to catch
    meetings posted before the window and filter on the meeting date itself."""
    found = []
    for chamber in ("house", "senate"):
        for row in _paged(f"committee-meeting/{CONGRESS}/{chamber}", "committeeMeetings",
                          start - timedelta(days=21), date.today()):
            detail = (_get(row["url"]) or {}).get("committeeMeeting") or {}
            when = (detail.get("date") or "")[:10]
            if not when or not (start.isoformat() <= when <= end.isoformat()):
                continue
            committees = "; ".join(c.get("name", "") for c in detail.get("committees") or [])
            title = detail.get("title") or ""
            if not (CHINA.search(title) or CHINA_COMMITTEES.search(committees)):
                continue
            found.append({
                "date": when, "chamber": chamber.title(), "committee": committees,
                "title": re.sub(r"\s+", " ", title).strip(),
                "type": detail.get("type") or "Meeting",
                "status": detail.get("meetingStatus") or "",
                "url": f"https://www.congress.gov/event/{CONGRESS}th-congress/{chamber}-event/{row.get('eventId')}",
            })
    return sorted(found, key=lambda h: h["date"])


def new_bills(start: date, end: date) -> list[dict]:
    """China-related bills and resolutions introduced start..end."""
    found = []
    for row in _paged(f"bill/{CONGRESS}", "bills", start, end):
        if not CHINA.search(row.get("title") or ""):
            continue
        typ, num = (row.get("type") or "").upper(), row.get("number")
        detail = (_get(f"bill/{CONGRESS}/{typ.lower()}/{num}") or {}).get("bill") or {}
        introduced = (detail.get("introducedDate") or "")[:10]
        if not introduced or not (start.isoformat() <= introduced <= end.isoformat()):
            continue
        sponsor = (detail.get("sponsors") or [{}])[0]
        found.append({
            "number": f"{'H.R.' if typ == 'HR' else 'S.' if typ == 'S' else typ} {num}",
            "title": row.get("title", "").strip(),
            "sponsor": sponsor.get("fullName", ""),
            "introduced": introduced,
            "url": f"https://www.congress.gov/bill/{CONGRESS}th-congress/{BILL_PATH.get(typ, 'house-bill')}/{num}",
        })
    return sorted(found, key=lambda b: b["introduced"])


def docket(back: tuple[date, date], ahead_days: int = 14) -> dict:
    """Hearings held in the window and scheduled for the next two weeks, plus new bills."""
    if not os.environ.get("CONGRESS_API_KEY"):
        return {}
    start, end = back
    return {"hearings": hearings(start, end + timedelta(days=ahead_days)),
            "bills": new_bills(start, end)}
