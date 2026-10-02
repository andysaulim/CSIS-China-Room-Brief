"""Gather the week's raw material for the brief.

Three inputs, all fetched at run time on GitHub Actions:

1. The China Daily Brief's published issues (its GitHub Pages archive keeps
   every day as YYYY-MM-DD.html). Each item carries the daily's headline,
   its sourced summary and the publisher URL.
2. The publisher's own headline for each priority-outlet story, read from the
   page's og:title, so In the News prints what the outlet ran rather than the
   daily's paraphrase. Paywalled pages still expose og:title.
3. Think-tank and CRS publications for Research Roundup. The daily collects
   these but no longer publishes them, so the weekly reads the feeds itself.

Every item gets a stable id. The model cites ids, never URLs, so a link in
the brief can only be one that was collected.
"""

from __future__ import annotations

import html as _html
import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote_plus

import requests

from . import config

UA = {"User-Agent": "CSISChinaRoomBrief/1.0 (+https://www.csis.org)"}
DAILY_PAGES = "https://andysaulim.github.io/Daily-China-Digest"


def _gnews(query: str) -> str:
    return f"https://news.google.com/rss/search?q={quote_plus(query)}+when:7d&hl=en-US&gl=US&ceid=US:en"


# Research Roundup sources. Direct feeds where the daily found one that works;
# Google News site searches elsewhere (same choices as the daily's Tier 2).
RESEARCH_FEEDS = {
    "RAND": "https://www.rand.org/topics/china.xml",
    "Brookings": _gnews("China site:brookings.edu"),
    "Carnegie Endowment": _gnews("China site:carnegieendowment.org"),
    "Council on Foreign Relations": _gnews("China site:cfr.org"),
    "Stimson Center": "https://www.stimson.org/feed/?topic=china",
    "German Marshall Fund": _gnews("China site:gmfus.org"),
    "Asia Society Policy Institute": _gnews("China site:asiasociety.org/policy-institute"),
    "AEI": _gnews("China site:aei.org"),
    "Hudson Institute": _gnews("China site:hudson.org"),
    "Heritage Foundation": _gnews("China site:heritage.org"),
    "CNAS": _gnews("China site:cnas.org"),
    "PIIE": _gnews("China site:piie.com"),
    "Rhodium Group": _gnews("China site:rhg.com"),
    "Hoover Institution": _gnews("China site:hoover.org"),
    "NBR": _gnews("China site:nbr.org"),
    "MERICS": _gnews("site:merics.org"),
    "Lowy Institute": "https://www.lowyinstitute.org/the-interpreter/rss.xml",
    "ASPI": "https://www.aspistrategist.org.au/feed/",
    "Jamestown Foundation": "https://jamestown.org/feed/",
    "Congressional Research Service": _gnews("China site:congress.gov/crs-product OR site:crsreports.congress.gov"),
}
_CHINA = re.compile(r"\b(China|Chinese|Beijing|Xi|PLA|Taiwan|PRC|CCP|Hong Kong|South China Sea)\b", re.I)


def _get(url: str, timeout: int = 20) -> requests.Response | None:
    try:
        r = requests.get(url, headers=UA, timeout=timeout)
        return r if r.ok else None
    except requests.RequestException:
        return None


# ---------- 1. the China Daily Brief archive ----------

def daily_items(start: date, end: date) -> tuple[list[dict], list[str]]:
    """Every item the daily ran between start and end, plus its Upcoming
    calendar lines. Returns (items, missing_dates)."""
    from bs4 import BeautifulSoup

    items, missing = [], []
    d = start
    while d <= end:
        r = _get(f"{DAILY_PAGES}/{d.isoformat()}.html")
        if not r:
            missing.append(d.isoformat())
            d += timedelta(days=1)
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        section = None
        for el in soup.find_all(["table", "div", "h3"]):
            cls = el.get("class") or []
            st = el.get("style") or ""
            if el.name == "table" and "sec-bar" in cls:
                section = el.get_text(" ", strip=True).lstrip("● ").strip()
            elif el.name == "div" and "border-left:3px" in st and "padding-left:12px" in st:
                divs = [x.get_text(" ", strip=True) for x in el.find_all("div", recursive=False)]
                a = el.find("a")
                if len(divs) >= 2 and a:
                    items.append({"date": d.isoformat(), "section": section, "tag": divs[0],
                                  "headline": divs[1], "body": divs[2] if len(divs) > 2 else "",
                                  "url": a["href"]})
            elif el.name == "h3":
                a = el.find("a")
                box = el.parent
                body = " ".join(p.get_text(" ", strip=True) for p in box.find_all(["p", "div"], recursive=False))
                if a:
                    items.append({"date": d.isoformat(), "section": "Top Stories", "tag": "",
                                  "headline": el.get_text(" ", strip=True), "body": body[:900],
                                  "url": a["href"]})
        d += timedelta(days=1)
    # one entry per URL, first appearance wins
    seen, out = set(), []
    for x in items:
        if x["url"] not in seen:
            seen.add(x["url"])
            out.append(x)
    return out, missing


# ---------- 2. publisher headlines ----------

_OG = re.compile(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', re.I)
_OG2 = re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title', re.I)


def original_headline(url: str) -> str:
    r = _get(url, timeout=12)
    if not r:
        return ""
    m = _OG.search(r.text[:200_000]) or _OG2.search(r.text[:200_000])
    if not m:
        return ""
    title = _html.unescape(m.group(1)).strip()
    # drop " | Reuters", " - The New York Times" and similar tails
    return re.split(r"\s+[|–-]\s+(?=[A-Z][\w .&']{1,40}$)", title)[0].strip()


def tag_outlets(items: list[dict], fetch_titles: bool = True) -> None:
    """Mark priority-outlet items and, where possible, attach the outlet's own headline."""
    from .daily_feed import host
    for x in items:
        hit = config.outlet_for(host(x["url"]))
        if hit:
            x["outlet_rank"], x["outlet"] = hit
            if fetch_titles:
                x["original_headline"] = original_headline(x["url"])


# ---------- 3. research ----------

def research_items(start: date, end: date) -> list[dict]:
    import feedparser

    lo = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    hi = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    out = []
    for inst, url in RESEARCH_FEEDS.items():
        r = _get(url)
        if not r:
            continue
        for e in feedparser.parse(r.content).entries[:40]:
            t = e.get("published_parsed") or e.get("updated_parsed")
            if not t:
                continue
            when = datetime(*t[:6], tzinfo=timezone.utc)
            if not (lo <= when < hi):
                continue
            title = _html.unescape(e.get("title", "")).strip()
            summary = re.sub(r"<[^>]+>", " ", e.get("summary", ""))
            if not _CHINA.search(title + " " + summary):
                continue
            # Google News titles end in " - Publisher"
            title = re.sub(r"\s+-\s+[^-]{2,60}$", "", title) if "news.google.com" in url else title
            out.append({"institution": inst, "title": title, "url": e.get("link", ""),
                        "date": when.date().isoformat(),
                        "summary": _html.unescape(re.sub(r"\s+", " ", summary)).strip()[:500]})
    return out


# ---------- the tracker ----------

def tracker_file(url: str, dest: str) -> str | None:
    """Download the ER tracker workbook. url is a direct-download link to the
    .xlsx, or to a native Google Sheet's export?format=xlsx endpoint."""
    r = _get(url, timeout=60)
    if not r or not r.content[:2] == b"PK":
        return None
    with open(dest, "wb") as f:
        f.write(r.content)
    return dest


def daily_upcoming(day: date) -> list[dict]:
    """The Upcoming calendar from the most recent daily issue on or before day."""
    from .horizon import parse_daily_upcoming
    for back in range(0, 4):
        d = day - timedelta(days=back)
        r = _get(f"{DAILY_PAGES}/{d.isoformat()}.html")
        if r:
            return parse_daily_upcoming(r.text, d)
    return []
