"""Talk Around Town: what the China accounts on X are talking about this week.

Sunday evening (weekly.py sweep):
  1. read Brian's list of X accounts (X_ACCOUNTS_URL, a Google Sheet);
  2. pull each account's posts from the past seven days through an Apify actor
     (APIFY_TOKEN; APIFY_ACTOR picks the actor). Apify scrapes X, which X's
     terms do not allow and which can break without notice; posts() is the only
     function that knows about it, so the X API can replace it in one place;
  3. group the China-relevant posts into topics with one Claude call, score
     each by engagement times the number of accounts on it, and write the top
     eight to the "Talk Around Town" tab of APPROVALS_SHEET_URL with a blank
     Status column.

Monday morning Brian types Approve (or Reject) in Status and may edit the
Topic and Summary text. The Monday-noon draft prints up to three approved
topics exactly as they stand in the sheet.
"""

from __future__ import annotations

import os
import re
from datetime import date, timedelta

import requests

from . import sheets

TAB = "Talk Around Town"
HEADERS = ["Status", "Week", "Topic", "Summary", "Accounts", "Top post", "Score"]
DEFAULT_ACTOR = "apidojo~tweet-scraper"
_CHINA = re.compile(r"\b(China|Chinese|PRC|CCP|Beijing|Xi|Taiwan|Hong Kong|PLA|South China Sea|Huawei|TikTok|"
                    r"tariff|export control|rare earth|Xinjiang|Tibet|Uyghur)", re.I)


def accounts(url: str) -> list[str]:
    """Handles from the accounts sheet: the column headed handle/account/username/X, or any @name or x.com link."""
    out = []
    for row in sheets.rows(url):
        cells = list(row.items())
        pick = [v for k, v in cells if re.search(r"handle|account|user|twitter|\bx\b", str(k), re.I)] or [v for _, v in cells]
        for v in pick:
            m = re.search(r"(?:x\.com/|twitter\.com/|@)([A-Za-z0-9_]{1,15})", str(v)) or \
                re.fullmatch(r"\s*([A-Za-z0-9_]{1,15})\s*", str(v))
            if m and m.group(1).lower() not in {h.lower() for h in out}:
                out.append(m.group(1))
                break
    return out


def _num(x) -> int:
    try:
        return int(x or 0)
    except (TypeError, ValueError):
        return 0


def posts(handles: list[str], since: date) -> list[dict]:
    """The accounts' posts since `since`, newest first, via Apify."""
    token = os.environ.get("APIFY_TOKEN", "")
    if not token:
        raise RuntimeError("APIFY_TOKEN is not set")
    actor = os.environ.get("APIFY_ACTOR", "").strip() or DEFAULT_ACTOR
    terms = [" OR ".join(f"from:{h}" for h in handles[i:i + 10]) + f" since:{since.isoformat()}"
             for i in range(0, len(handles), 10)]
    r = requests.post(f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items",
                      params={"token": token, "timeout": 280},
                      json={"searchTerms": terms, "sort": "Latest", "maxItems": 60 * len(handles)}, timeout=300)
    if not r.ok:
        raise RuntimeError(f"Apify {r.status_code}: {r.text[:200]}")
    out, seen = [], set()
    for t in r.json():
        url = t.get("url") or t.get("twitterUrl") or ""
        text = t.get("fullText") or t.get("text") or ""
        author = (t.get("author") or {}).get("userName") or t.get("username") or ""
        if not url or url in seen or not text:
            continue
        seen.add(url)
        out.append({"id": f"P{len(out) + 1}", "url": url, "author": author, "text": re.sub(r"\s+", " ", text),
                    "created": str(t.get("createdAt", ""))[:30],
                    "engagement": sum(_num(t.get(k)) for k in ("likeCount", "retweetCount", "replyCount", "quoteCount"))})
    return out


TOPIC_SYSTEM = """You group posts by influential China watchers on X into the week's trending topics for a CSIS internal brief.

- Use only the posts given. Do not add facts, names or figures that no post states.
- A topic is one event or debate that several posts address. Ignore posts unrelated to China or U.S.-China relations, and personal or promotional posts.
- title: what the topic is, under 70 characters, plain words, sentence case, no metaphors.
- summary: one or two sentences, under 45 words, on what the accounts are saying, attributing views to them ("Several analysts argued ..."). Write "U.S." never "US". No em dashes.
- post_ids: every post that belongs to the topic.
- Return up to ten topics."""

TOPIC_SCHEMA = {
    "type": "object",
    "properties": {"topics": {"type": "array", "items": {
        "type": "object",
        "properties": {"title": {"type": "string"}, "summary": {"type": "string"},
                       "post_ids": {"type": "array", "items": {"type": "string"}}},
        "required": ["title", "summary", "post_ids"], "additionalProperties": False}}},
    "required": ["topics"],
    "additionalProperties": False,
}


def topics(all_posts: list[dict], keep: int = 8) -> list[dict]:
    from .compose import ask
    china = [p for p in all_posts if _CHINA.search(p["text"])] or all_posts
    by_id = {p["id"]: p for p in china}
    text = "\n".join(f"{p['id']} | @{p['author']} | {p['created']} | engagement {p['engagement']}\n   {p['text'][:600]}"
                     for p in china[:600])
    found = ask(TOPIC_SYSTEM, "Posts:\n" + text, TOPIC_SCHEMA, max_tokens=32000)["topics"]
    out = []
    for t in found:
        ps = [by_id[i] for i in t["post_ids"] if i in by_id]
        if not ps:
            continue
        authors = sorted({p["author"] for p in ps}, key=str.lower)
        top = max(ps, key=lambda p: p["engagement"])
        out.append({"title": t["title"].strip(), "summary": re.sub(r"\s*—\s*", ", ", t["summary"]).strip(),
                    "accounts": authors, "top_post": top["url"],
                    "score": sum(p["engagement"] for p in ps) * len(authors)})
    return sorted(out, key=lambda t: -t["score"])[:keep]


def sweep(issue_date: date) -> list[dict]:
    """Run the week's sweep and write candidates for Brian to approve."""
    handles = accounts(os.environ.get("X_ACCOUNTS_URL", ""))
    print(f"X accounts: {len(handles)}")
    if not handles:
        raise RuntimeError("no X accounts read from X_ACCOUNTS_URL")
    ps = posts(handles, issue_date - timedelta(days=8))
    print(f"posts pulled: {len(ps)}")
    found = topics(ps)
    rows = [["", issue_date.isoformat(), t["title"], t["summary"], ", ".join("@" + a for a in t["accounts"]),
             t["top_post"], t["score"]] for t in found]
    sheets.append(os.environ["APPROVALS_SHEET_URL"], TAB, HEADERS, rows)
    print(f"candidates written to '{TAB}': {len(rows)}")
    return found


def approved(issue_date: date, limit: int = 3) -> tuple[list[dict], str]:
    """This week's topics marked Approve, as brief items, plus a note for the run log.
    When Brian has approved none, the top three unreviewed candidates are used and the note says so."""
    url = os.environ.get("APPROVALS_SHEET_URL", "")
    if not url:
        return [], "APPROVALS_SHEET_URL not set"
    try:
        rows = [r for r in sheets.rows(url, TAB) if str(r.get("Week", "")).strip()[:10] == issue_date.isoformat()]
    except Exception as e:      # a missing tab or sheet must not stop the draft
        return [], f"approvals sheet unreadable: {e}"
    ok = [r for r in rows if str(r.get("Status", "")).strip().lower().startswith("approve")]
    note = f"{len(ok)} approved of {len(rows)} candidates"
    if not ok:
        ok = [r for r in rows if not str(r.get("Status", "")).strip().lower().startswith("reject")]
        note += "; none approved, using the top unreviewed candidates (marked unapproved)"
    items = []
    for r in ok[:limit]:
        handles = [h.strip() for h in str(r.get("Accounts", "")).split(",") if h.strip()]
        shown = ", ".join(handles[:3]) + (f" and {len(handles) - 3} more" if len(handles) > 3 else "")
        items.append({"tag": shown, "headline": str(r.get("Topic", "")).strip(),
                      "body": str(r.get("Summary", "")).strip(), "url": str(r.get("Top post", "")).strip(),
                      "approved": str(r.get("Status", "")).strip().lower().startswith("approve")})
    return items, note
