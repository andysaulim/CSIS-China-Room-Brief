"""Read each research candidate's own page before the model sees it.

Google News feeds carry a title and a redirect link and nothing else, so the
model had no argument to summarize and restated titles instead. This resolves
the link to the publisher, then pulls the authors, the page's own summary
line and the opening paragraphs, so Research Roundup can say what a piece
argues and who wrote it.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor

import requests

from .collect import BROWSER_UA, publisher_url

_SKIP = re.compile(r"cookie|subscribe|newsletter|sign up|all rights reserved|javascript|share this", re.I)


def _meta(soup, *names) -> str:
    for n in names:
        tag = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n})
        if tag and tag.get("content", "").strip():
            return tag["content"].strip()
    return ""


def _authors(soup) -> list[str]:
    found = [m.get("content", "").strip() for m in soup.find_all("meta", attrs={"name": "citation_author"})]
    if not found:
        for block in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(block.string or "")
            except ValueError:
                continue
            for node in data if isinstance(data, list) else data.get("@graph", [data]):
                a = node.get("author") if isinstance(node, dict) else None
                for x in (a if isinstance(a, list) else [a] if a else []):
                    name = x.get("name") if isinstance(x, dict) else x
                    if isinstance(name, str) and name.strip():
                        found.append(name.strip())
            if found:
                break
    if not found:
        a = _meta(soup, "author", "article:author", "parsely-author", "sailthru.author")
        if a and not a.startswith("http"):
            found = [x.strip() for x in re.split(r",| and ", a) if x.strip()]
    # institutions sometimes list themselves as the author
    out = []
    for n in found:
        if n not in out and len(n.split()) <= 5 and not re.search(r"Institut|Foundation|Center|Council|Endowment|Brookings", n):
            out.append(n)
    return out[:4]


def _opening(soup, limit: int = 1400) -> str:
    body = soup.find("article") or soup.find("main") or soup
    paras = []
    for p in body.find_all("p"):
        t = re.sub(r"\s+", " ", p.get_text(" ", strip=True))
        if len(t) > 80 and not _SKIP.search(t):
            paras.append(t)
        if sum(map(len, paras)) > limit:
            break
    return " ".join(paras)[:limit]


def read(url: str) -> dict:
    from bs4 import BeautifulSoup

    url = publisher_url(url)
    out = {"url": url, "authors": [], "description": "", "text": ""}
    if "news.google.com" in url:
        return out
    try:
        r = requests.get(url, headers=BROWSER_UA, timeout=15)
        if not r.ok:
            return out
        out["url"] = r.url or url
    except requests.RequestException:
        return out
    soup = BeautifulSoup(r.text[:600_000], "html.parser")
    out["authors"] = _authors(soup)
    out["description"] = _meta(soup, "og:description", "description", "twitter:description")
    out["text"] = _opening(soup)
    return out


def research(items: list[dict]) -> int:
    """Fill url, authors and text on each research item in place. Returns how many pages were read."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        pages = list(pool.map(lambda x: read(x["url"]), items))
    n = 0
    for x, p in zip(items, pages):
        x["url"] = p["url"]
        x["authors"] = p["authors"]
        if p["text"] or p["description"]:
            n += 1
            x["summary"] = " ".join(s for s in (p["description"], p["text"]) if s)[:1600]
    return n
