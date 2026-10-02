"""Draft the week's copy with Claude from the collected corpus.

The model sees numbered sources (N for news, R for research) and returns
source ids, never URLs, through a JSON schema. Links and outlet names are
filled in from the corpus afterwards, so a link in the brief can only be one
the collector found. Same rule as the daily brief: every claim traces to a
collected item, and an omission beats an invention.
"""

from __future__ import annotations

import json
import os
import re

import anthropic

MODEL = "claude-opus-5-5"

STYLE = {
    "house": (
        "Write in the house style of a CSIS internal brief: write \"U.S.\" never \"US\"; plain declarative sentences, numbers over "
        "adjectives, named actors, dated events. Headlines under 60 characters, in sentence case. Each item "
        "is one or two sentences. Lead with what happened, not with background. No bold labels, no bullets, "
        "no rhetorical questions, no em-dashes. Leave why and bullets empty. Vary sentence length. Headlines say what happened in plain "
        "words: no metaphors, wordplay or question headlines. Avoid: underscore, landscape, navigate, robust, "
        "pivotal, key takeaway, it remains to be seen, it is important to note. Use the sources' own wording "
        "where you can."),
    "brevity": (
        "Write in Axios Smart Brevity: headline under 60 characters; a one-sentence lede saying what is new; "
        "optionally a one-sentence 'why' and up to three short bullets. Plain words, subject-verb-object. "
        "No em-dashes."),
}

SYSTEM = """You draft the CSIS China Room Brief, a weekly internal email on US-China relations that goes out on Fridays to CSIS staff.

Rules that are never broken:
- Every sentence must be supported by the numbered sources provided. Do not add facts, dates, figures, titles or quotes from memory. If a source does not say it, leave it out.
- Quote only words that appear in a source, inside quotation marks, attributed.
- Cite each item with the id of the source it rests on (N12, R3). Never write a URL.
- Name the outlet in the text when a claim comes from reporting ("Reuters reported").
- Prefer US-China relations over China's domestic news when choosing what leads.

Sections:
- re_line: four or five short phrases separated by commas, the week's main threads.
- editors_note: one or two sentences, under 40 words, plain and direct.
- week_at_a_glance: exactly three things scheduled or expected in the coming week that matter for U.S.-China relations (trade, Taiwan, security, technology, diplomacy, Congress), from the sources only; one or two sentences each. Skip domestic Chinese consumer or travel stories.
- heard_on_the_hill: three to five items on Congress (members, bills, hearings, letters) from the past week. Sources marked "Congress.gov" are the official record of hearings and newly introduced bills: flag the most significant ones here, and use scheduled hearings in week_at_a_glance.
- in_the_news: the five most important China stories of the past week from the priority-outlet sources (marked [priority tier N], tier 1 best), ranked by importance to U.S.-China relations; a story many outlets covered outranks one only a single outlet ran. Count each story once. Set source_id to the item from the best-tier outlet that covered it (New York Times, Wall Street Journal and Washington Post are tier 1; Bloomberg and Financial Times tier 2; Reuters and AP tier 3), and list every other source on the same story in also_ids. Give each a summary (body) of two sentences and under 60 words saying what happened, drawing on every source that covered the story and naming outlets for claims; leave why empty unless the style asks for it.
- research_roundup: three to six publications from the R sources, at most one per institution. Prefer U.S. institutions (Brookings, CFR, Carnegie, RAND, CNAS, AEI, Hudson, Heritage, PIIE, Stimson, Hoover) and the Congressional Research Service; use non-U.S. institutions only to fill. For each, one sentence on the argument or finding, naming the authors when the source does."""

ITEM = {
    "type": "object",
    "properties": {
        "source_id": {"type": "string"},
        "tag": {"type": "string", "description": "Short label and date, e.g. 'Senate, Oct 1'"},
        "headline": {"type": "string"},
        "body": {"type": "string"},
        "why": {"type": "string"},
        "bullets": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["source_id", "tag", "headline", "body", "why", "bullets"],
    "additionalProperties": False,
}
SCHEMA = {
    "type": "object",
    "properties": {
        "re_line": {"type": "string"},
        "editors_note": {"type": "string"},
        "week_at_a_glance": {"type": "array", "items": ITEM},
        "heard_on_the_hill": {"type": "array", "items": ITEM},
        "in_the_news": {"type": "array", "items": {
            "type": "object",
            "properties": {"source_id": {"type": "string"},
                           "headline": {"type": "string", "description": "The source's headline in sentence case, wording unchanged"},
                           "also_ids": {"type": "array", "items": {"type": "string"},
                                        "description": "Other source ids covering the same story"},
                           "body": {"type": "string"}, "why": {"type": "string"}},
            "required": ["source_id", "headline", "also_ids", "body", "why"], "additionalProperties": False}},
        "research_roundup": {"type": "array", "items": {
            "type": "object",
            "properties": {"source_id": {"type": "string"}, "body": {"type": "string"}},
            "required": ["source_id", "body"], "additionalProperties": False}},
    },
    "required": ["re_line", "editors_note", "week_at_a_glance", "heard_on_the_hill",
                 "in_the_news", "research_roundup"],
    "additionalProperties": False,
}


def corpus(news: list[dict], research: list[dict]) -> tuple[str, dict]:
    """Number every source; return the prompt text and an id -> source map."""
    index, lines = {}, []
    for n, x in enumerate(news, 1):
        sid = f"N{n}"
        index[sid] = {"kind": "news", **x}
        pri = f" [priority tier {x['outlet_rank']}: {x['outlet']}]" if x.get("outlet") else ""
        lines.append(f"{sid} | {x['date']} | {x.get('section') or ''} | {x.get('tag') or ''}{pri}\n"
                     f"   {x['headline']}\n   {x.get('body', '')}")
    for n, x in enumerate(research, 1):
        sid = f"R{n}"
        index[sid] = {"kind": "research", **x}
        lines.append(f"{sid} | {x['date']} | {x['institution']}\n   {x['title']}\n   {x.get('summary', '')}")
    return "\n".join(lines), index


def draft(news, research, calendar_lines: list[str], window: str, style: str = "house") -> dict:
    text, index = corpus(news, research)
    user = (f"Week covered: {window}.\nStyle: {STYLE[style]}\n\n"
            f"Scheduled items from the editorial calendar (usable for Week at a Glance):\n"
            + ("\n".join(calendar_lines) or "(none)") + "\n\nSources:\n" + text)
    # A key that is not scoped to a workspace must name one on every request.
    ws = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
    client = anthropic.Anthropic(default_headers={"anthropic-workspace-id": ws} if ws else None)
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        # On a policy decline, re-run on Anthropic's recommended fallback model.
        fallbacks="default",
        system=SYSTEM,
        output_config={"effort": "high",
                       "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": user}],
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"model declined: {resp.stop_details}")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("draft hit max_tokens")
    raw = next(b.text for b in resp.content if b.type == "text")
    copy = resolve(json.loads(raw), index)
    if style == "house":
        # House style carries no signposts: fold any why or bullets into the paragraph.
        for sec in ("week_at_a_glance", "heard_on_the_hill", "in_the_news"):
            for it in copy.get(sec, []):
                extra = " ".join(x for x in [it.pop("why", "")] + it.pop("bullets", []) if x)
                if extra:
                    it["body"] = (it.get("body", "") + " " + extra).strip()
    return copy


def _clean(s: str) -> str:
    """Zero em-dashes in what ships; flagging the rest is the reviewer's job."""
    s = re.sub(r"\s*—\s*", ", ", s or "")
    return s.strip()


def resolve(out: dict, index: dict) -> dict:
    """Replace source ids with links and outlet names; drop anything uncited."""
    copy = {"re_line": _clean(out["re_line"]), "editors_note": _clean(out["editors_note"]),
            "warnings": []}
    for sec in ("week_at_a_glance", "heard_on_the_hill"):
        copy[sec] = []
        for it in out[sec]:
            src = index.get(it["source_id"])
            if not src:
                copy["warnings"].append(f"{sec}: dropped item citing unknown {it['source_id']}")
                continue
            if len(it["headline"]) > 60:
                copy["warnings"].append(f"{sec}: headline over 60 characters: {it['headline']}")
            copy[sec].append({"tag": it["tag"].replace(" \u00b7 ", ", "),
                              "headline": _clean(it["headline"]), "body": _clean(it["body"]),
                              "why": _clean(it.get("why", "")),
                              "bullets": [_clean(b) for b in it.get("bullets", [])],
                              "url": src.get("url", "")})
    copy["in_the_news"] = []
    for it in out["in_the_news"][:5]:
        # Link the best-ranked priority outlet that ran the story, whatever id the model led with.
        ids = [it["source_id"]] + list(it.get("also_ids") or [])
        cands = [index[i] for i in ids if i in index and index[i].get("outlet")]
        if not cands:
            copy["warnings"].append(f"in_the_news: dropped {it['source_id']} (unknown or not a priority outlet)")
            continue
        src = min(cands, key=lambda x: x["outlet_rank"])
        lead = index.get(it["source_id"], {})
        own = src.get("original_headline", "")
        if src is lead:
            headline = own if own and not _title_case(own) else (it.get("headline") or own or src["headline"])
        else:
            headline = own if own and not _title_case(own) else src["headline"]
        d = src["date"]
        copy["in_the_news"].append({
            "tag": f"{src['outlet']}, {_md(d)}",
            "headline": _clean(headline),
            "body": _clean(it.get("body", "")), "why": _clean(it.get("why", "")),
            "url": src["url"]})
    copy["research_roundup"] = []
    used = set()
    for it in out["research_roundup"]:
        src = index.get(it["source_id"])
        if not src or src["kind"] != "research":
            copy["warnings"].append(f"research_roundup: dropped {it['source_id']}")
            continue
        if src["institution"] in used:
            copy["warnings"].append(f"research_roundup: dropped a second {src['institution']} item")
            continue
        used.add(src["institution"])
        copy["research_roundup"].append({"institution": src["institution"], "date": _md(src["date"]),
                                         "headline": src["title"], "body": _clean(it["body"]),
                                         "url": src["url"]})
    return copy


def _title_case(h: str) -> bool:
    """True for Title Case Headlines, which read out of place in a sentence-case brief."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'’]*", h) if len(w) > 3]
    return len(words) >= 3 and sum(w[0].isupper() for w in words) / len(words) > 0.75


def _md(iso: str) -> str:
    from datetime import date
    d = date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}"
