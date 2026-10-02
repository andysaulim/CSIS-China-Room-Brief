"""Look-back material from the China Daily Brief.

Today this reads the daily's published_ledger.json (14 days of headline + URL
for every item it ran) and public/archive.json (each issue's RE line). That is
enough for In the News and for Heard on the Hill candidates. It is not enough
for Research Roundup: the daily stopped publishing think-tank and journal items
in 2026, so they never reach the ledger. See README, "Daily pipeline changes".
"""

from __future__ import annotations

import json
import re
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from . import config


def _read(src: str):
    if re.match(r"^https?://", src):
        with urllib.request.urlopen(src, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    return json.loads(Path(src).read_text(encoding="utf-8"))


def load_ledger(src: str = config.DAILY_LEDGER) -> list[dict]:
    data = _read(src)
    return data["entries"] if isinstance(data, dict) else data


def load_archive(src: str = config.DAILY_ARCHIVE) -> list[dict]:
    return _read(src)


def in_window(entries, start: date, end: date):
    s, e = start.isoformat(), end.isoformat()
    return [x for x in entries if s <= x.get("date", "") <= e]


def host(url: str) -> str:
    h = (urlparse(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def priority_items(entries):
    """Ledger items from the priority outlet list, best-ranked outlet first."""
    out = []
    for x in entries:
        hit = config.outlet_for(host(x["url"]))
        if hit:
            rank, name = hit
            out.append({**x, "outlet": name, "rank": rank})
    return sorted(out, key=lambda x: (x["rank"], x["date"]))


def hill_candidates(entries):
    """Congress-related items, any outlet, for the coordinator to write from."""
    pat = re.compile(config.HILL_PATTERN, re.I)
    nope = re.compile(config.NOT_HILL_PATTERN)
    seen, out = set(), []
    for x in sorted(entries, key=lambda x: x["date"]):
        key = x["headline"].lower()[:60]
        if key in seen or not pat.search(x["headline"]) or nope.search(x["headline"]):
            continue
        seen.add(key)
        hit = config.outlet_for(host(x["url"]))
        out.append({**x, "outlet": hit[1] if hit else host(x["url"])})
    return out


def coverage_clusters(entries, groups: dict[str, list[str]]):
    """Count distinct priority outlets per story, given keyword groups.

    'Most discussed' is defined as the story the most priority outlets carried
    that week. In production Claude does the clustering; this keyword form is
    for the sample and for testing that ranking.
    """
    counts = defaultdict(set)
    for x in priority_items(entries):
        for story, kws in groups.items():
            if all(re.search(k, x["headline"], re.I) for k in kws):
                counts[story].add(x["outlet"])
    return sorted(((s, sorted(o)) for s, o in counts.items()), key=lambda t: -len(t[1]))


def forward_candidates(entries):
    """Headlines that point at the coming week: scheduled moves, deadlines,
    'within weeks'. Candidates for the human-written Week at a Glance."""
    pat = re.compile(r"\b(within weeks|next week|deadline|until|till|no date set|"
                     r"set to|to meet|expected|extends?)\b", re.I)
    out = []
    for x in priority_items(entries):
        if pat.search(x["headline"]):
            out.append(x)
    return sorted(out, key=lambda x: x["date"], reverse=True)
