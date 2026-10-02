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
        "adjectives, named actors, dated events. Headlines under 60 characters, in sentence case. Items run "
        "one to three sentences and should not all be the same length. Lead with what happened, not with background. No bold labels, no bullets, "
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

Every item carries an event label: the underlying event in a few words, worded identically wherever that event recurs in any section.

Prose (every section):
- Name the outlet once per item, where the claim first appears. Do not end every sentence with "X reported."
- Vary the shape of items. Some are one sentence, some two or three. Lead some with the figure, the quote or the place, not always with the actor.
- Write months in full ("September 30"), never "Sept." or "Oct.". No em dashes.

Sections:
- re_line: four or five short phrases separated by commas, the week's main threads.
- editors_note: one or two sentences, under 40 words, on what the week's stories add up to for U.S.-China relations. Do not restate the top In the News story. Leave it empty if there is no through-line.
- week_at_a_glance: three or four items, never fewer than three, on what is coming in the seven days after the issue date that matters for U.S.-China relations. Fill in this order until there are at least three: (1) G sources marked [this week]; (2) N sources that state a specific date inside those seven days; (3) G sources marked [following week], which still lead the section with their own date; (4) N sources reporting a decision, vote, deadline, release or meeting expected in the coming days without an exact date, tagged with the topic and "this week". For a G source, source_id is the G id and the tag is left empty (it is filled from the calendar); for an N source, the tag is the topic and the date ("Trade, October 7"). Say what happens and what to watch, with any N sources that explain the stakes in context_ids.
- heard_on_the_hill: three to five items on Congress (members, bills, hearings, letters) from the past week, one per thread: several reports on the same bill, hold or arms package are one item, folded together. Prefer primary sources (marked [primary], including Congress.gov records of hearings and newly introduced bills), then U.S. outlets; use a non-U.S. outlet only when nothing else covers the item. Put the best source in source_id and the others in context_ids.
- in_the_news: the five most important China events of the past week from the priority-outlet sources (marked [priority tier N], tier 1 best), ranked by importance to U.S.-China relations. Five distinct events: reactions to, follow-ups of and side deals from one event are that event, so fold them into its summary instead of giving them a slot. A story many outlets covered outranks one only a single outlet ran. Set source_id to the item from the best-tier outlet that covered it (New York Times, Wall Street Journal and Washington Post are tier 1; Bloomberg and Financial Times tier 2; Reuters and AP tier 3), and list every other source on the same event in also_ids. Give each a summary (body) of two or three sentences, under 70 words, drawing on every source that covered it; leave why empty unless the style asks for it.
- research_roundup: three to six publications from the R sources, at most one per institution and at most two on the same news event. Prefer U.S. institutions (Brookings, CFR, Carnegie, RAND, CNAS, AEI, Hudson, Heritage, PIIE, Stimson, Hoover) and the Congressional Research Service; use non-U.S. institutions only to fill. For each, one or two sentences on what the piece argues or finds, from its text, naming the authors listed. Never restate the title. Skip an R source that has no text beyond its title."""

ITEM = {
    "type": "object",
    "properties": {
        "source_id": {"type": "string"},
        "tag": {"type": "string", "description": "Short label and date, e.g. 'Senate, Oct 1'"},
        "headline": {"type": "string"},
        "body": {"type": "string"},
        "why": {"type": "string"},
        "bullets": {"type": "array", "items": {"type": "string"}},
        "context_ids": {"type": "array", "items": {"type": "string"}},
        "event": {"type": "string", "description": "Short name of the underlying event, the same wording wherever it recurs, e.g. 'Trump-Xi Washington summit'"},
    },
    "required": ["source_id", "tag", "headline", "body", "why", "bullets", "context_ids", "event"],
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
                           "body": {"type": "string"}, "why": {"type": "string"},
                           "event": {"type": "string", "description": "Short name of the underlying event, the same wording wherever it recurs, e.g. 'Trump-Xi Washington summit'"}},
            "required": ["source_id", "headline", "also_ids", "body", "why", "event"], "additionalProperties": False}},
        "research_roundup": {"type": "array", "items": {
            "type": "object",
            "properties": {"source_id": {"type": "string"}, "body": {"type": "string"},
                           "event": {"type": "string", "description": "Short name of the underlying event, the same wording wherever it recurs, e.g. 'Trump-Xi Washington summit'"}},
            "required": ["source_id", "body", "event"], "additionalProperties": False}},
    },
    "required": ["re_line", "editors_note", "week_at_a_glance", "heard_on_the_hill",
                 "in_the_news", "research_roundup"],
    "additionalProperties": False,
}


def corpus(news: list[dict], research: list[dict], glance: list[dict] | None = None) -> tuple[str, dict]:
    """Number every source; return the prompt text and an id -> source map."""
    index, lines = {}, []
    for n, e in enumerate(glance or [], 1):
        sid = f"G{n}"
        index[sid] = {"kind": "glance", **e}
        when = e["start"].isoformat() + (f" to {e['end'].isoformat()}" if e["end"] != e["start"] else "")
        where = f", {e['where']}" if e.get("where") else ""
        lines.append(f"{sid} | {when} | [{e.get('window', 'this week')}] | {e['type']} | from {e['source']}\n   {e['title']}{where}\n   {e.get('angle', '')}")
    for n, x in enumerate(news, 1):
        sid = f"N{n}"
        index[sid] = {"kind": "news", **x}
        pri = f" [priority tier {x['outlet_rank']}: {x['outlet']}]" if x.get("outlet") else ""
        if x.get("primary") or (x.get("section") or "").startswith("Congress.gov"):
            pri += f" [primary: {x.get('primary') or 'Congress.gov'}]"
        lines.append(f"{sid} | {x['date']} | {x.get('section') or ''} | {x.get('tag') or ''}{pri}\n"
                     f"   {x['headline']}\n   {x.get('body', '')}")
    for n, x in enumerate(research, 1):
        sid = f"R{n}"
        index[sid] = {"kind": "research", **x}
        by = f" | by {', '.join(x['authors'])}" if x.get("authors") else ""
        lines.append(f"{sid} | {x['date']} | {x['institution']}{by}\n   {x['title']}\n   "
                     f"{x.get('summary') or '(title only)'}")
    return "\n".join(lines), index


def draft(news, research, glance: list[dict], window: str, style: str = "house") -> dict:
    text, index = corpus(news, research, glance)
    user = (f"Week covered: {window}.\nStyle: {STYLE[style]}\n\n"
            f"G sources are the calendar for the two weeks after the issue date. Week at a Glance needs at least "
            f"three items.\n\nSources:\n" + text)
    # A key that is not scoped to a workspace must name one on every request.
    ws = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
    client = anthropic.Anthropic(default_headers={"anthropic-workspace-id": ws} if ws else None)
    # Streamed: with the larger corpus and high effort, thinking plus the JSON
    # outgrew 16k tokens, and a non-streamed call this large times out.
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=64000,
        betas=["server-side-fallback-2026-07-01"],
        # On a policy decline, re-run on Anthropic's recommended fallback model.
        fallbacks="default",
        system=SYSTEM,
        output_config={"effort": "high",
                       "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": user}],
    ) as stream:
        resp = stream.get_final_message()
    print(f"model usage: {resp.usage.input_tokens} in, {resp.usage.output_tokens} out")
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
    copy["week_at_a_glance"] = []
    for it in out["week_at_a_glance"][:4]:
        src = index.get(it["source_id"])
        ctx = [index[i] for i in it.get("context_ids") or [] if i in index and index[i]["kind"] == "news"]
        if src and src["kind"] == "glance":
            item = _item(it, copy, "week_at_a_glance", tag=f"{src['type']}, {_span(src['start'], src['end'])}",
                         url=src.get("url") or (ctx[0]["url"] if ctx else ""), iso=src["start"].isoformat())
            item["calendar_title"] = src["title"]
        elif src and src["kind"] == "news" and it.get("tag", "").strip():
            item = _item(it, copy, "week_at_a_glance", tag=it["tag"], url=src.get("url", ""), iso="")
            item["from_news"] = True
        else:
            copy["warnings"].append(f"week_at_a_glance: dropped {it['source_id']} (no dated calendar entry)")
            continue
        copy["week_at_a_glance"].append(item)
    if len(copy["week_at_a_glance"]) < 3:
        copy["warnings"].append(f"week_at_a_glance: only {len(copy['week_at_a_glance'])} items; three is the minimum")
    copy["heard_on_the_hill"] = []
    for it in out["heard_on_the_hill"][:5]:
        cands = [index[i] for i in [it["source_id"]] + list(it.get("context_ids") or [])
                 if i in index and index[i]["kind"] == "news"]
        if not cands:
            copy["warnings"].append(f"heard_on_the_hill: dropped item citing unknown {it['source_id']}")
            continue
        src = min(cands, key=_hill_rank)       # link the primary record when there is one
        copy["heard_on_the_hill"].append(_item(it, copy, "heard_on_the_hill", tag=it["tag"],
                                               url=src.get("url", ""), iso=src["date"]))
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
            "iso": d, "event": it.get("event", ""), "tag": f"{src['outlet']}, {_md(d)}",
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
                                         "iso": src["date"], "authors": src.get("authors", []),
                                         "event": it.get("event", ""),
                                         "headline": src["title"], "body": _clean(it["body"]),
                                         "url": src["url"]})
    return copy


def _item(it, copy, sec, *, tag, url, iso) -> dict:
    if len(it["headline"]) > 60:
        copy["warnings"].append(f"{sec}: headline over 60 characters: {it['headline']}")
    return {"tag": tag.replace(" \u00b7 ", ", "), "headline": _clean(it["headline"]), "body": _clean(it["body"]),
            "why": _clean(it.get("why", "")), "bullets": [_clean(b) for b in it.get("bullets", [])],
            "url": url, "iso": iso, "event": it.get("event", "")}


def _hill_rank(src: dict) -> int:
    """Congress.gov and committee releases first, then priority outlets by tier, then the rest."""
    if src.get("primary") or (src.get("section") or "").startswith("Congress.gov"):
        return 0
    return src.get("outlet_rank") or 99


def _span(s, e) -> str:
    if s == e:
        return f"{s.strftime('%B')} {s.day}"
    if s.month == e.month:
        return f"{s.strftime('%B')} {s.day}\u2013{e.day}"
    return f"{s.strftime('%B')} {s.day} to {e.strftime('%B')} {e.day}"


def _title_case(h: str) -> bool:
    """True for Title Case Headlines, which read out of place in a sentence-case brief."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'’]*", h) if len(w) > 3]
    return len(words) >= 3 and sum(w[0].isupper() for w in words) / len(words) > 0.75


def _md(iso: str) -> str:
    from datetime import date
    d = date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}"
