"""Draft the week's copy with Claude from the collected corpus.

The model sees numbered sources (N for Congress news and records, R for CSIS
research, E for engagement form submissions) and returns source ids, never
URLs, through a JSON schema. Links are filled in from the corpus afterwards,
so a link in the brief can only be one the collector found. Every claim traces
to a collected item, and an omission beats an invention.

Talk Around Town is not drafted here: Brian approves topics in the sweep's
sheet (x_sweep.py), and the brief prints them as approved.
"""

from __future__ import annotations

import json
import os
import re
from urllib.parse import urlparse

import anthropic

from . import config

MODEL = "claude-opus-5-5"

STYLE = {
    "house": (
        "Write in the house style of a CSIS internal brief: write \"U.S.\" never \"US\"; plain declarative sentences, numbers over "
        "adjectives, named actors, dated events. Headlines under 60 characters, in sentence case. Lead with what "
        "happened, not with background. No bold labels, no bullets, no rhetorical questions, no em-dashes. Headlines "
        "say what happened in plain words: no metaphors, wordplay or question headlines. Avoid: underscore, "
        "landscape, navigate, robust, pivotal, key takeaway, it remains to be seen, it is important to note. Use "
        "the sources' own wording where you can."),
    "brevity": (
        "Write in Axios Smart Brevity: headline under 60 characters; a one-sentence lede saying what is new. "
        "Plain words, subject-verb-object. No em-dashes."),
}

SYSTEM = """You draft the CSIS China Room Engagement Brief, a weekly internal email for CSIS staff on Congress and CSIS's own China work. It goes out on Tuesdays.

Rules that are never broken:
- Every sentence must be supported by the numbered sources provided. Do not add facts, dates, figures, titles or quotes from memory. If a source does not say it, leave it out.
- Quote only words that appear in a source, inside quotation marks, attributed.
- Cite each item with the id of the source it rests on (N12, R3, E2). Never write a URL.
- Write months in full ("September 30"), never "Sept." or "Oct.". No em dashes.

Sections:
- heard_on_the_hill: up to five items on Congress and China from the past week (members, bills, hearings, letters, committee reports), one per thread: several reports on the same bill, hold or arms package are one item, folded together. Prefer primary sources (marked [primary], including Congress.gov records of hearings and newly introduced bills and committee releases), then U.S. outlets. Put the best source in source_id and the others in context_ids. One or two sentences each; name the outlet once when a claim comes from reporting.
- csis_research: up to five CSIS publications from the R sources released in the week covered. Prefer work on U.S.-China relations, then China, then the region. For each, ONE line of 25 words or fewer saying what the piece argues or finds, from its text, starting with the verb ("Argues ...", "Finds ..."); the authors print beside the line, so do not name them. Never restate the title; if an R source has only a title, leave line empty.
- csis_engagements: one entry per E source (form submissions on last week's CSIS policy engagements), ONE line of 25 words or fewer saying who engaged whom on what, using only what the submission says. Skip a submission that does not describe an engagement."""

ITEM = {
    "type": "object",
    "properties": {
        "source_id": {"type": "string"},
        "tag": {"type": "string", "description": "Short label and date, e.g. 'Senate, October 1'"},
        "headline": {"type": "string"},
        "body": {"type": "string"},
        "context_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["source_id", "tag", "headline", "body", "context_ids"],
    "additionalProperties": False,
}
LINE = {
    "type": "object",
    "properties": {"source_id": {"type": "string"}, "line": {"type": "string"}},
    "required": ["source_id", "line"],
    "additionalProperties": False,
}
SCHEMA = {
    "type": "object",
    "properties": {
        "heard_on_the_hill": {"type": "array", "items": ITEM},
        "csis_research": {"type": "array", "items": LINE},
        "csis_engagements": {"type": "array", "items": LINE},
    },
    "required": ["heard_on_the_hill", "csis_research", "csis_engagements"],
    "additionalProperties": False,
}


def ask(system: str, user: str, schema: dict, max_tokens: int = 64000) -> dict:
    """One structured Claude call; returns the parsed JSON. Streamed, because a large
    budget at high effort outruns a non-streamed request."""
    # A key that is not scoped to a workspace must name one on every request.
    ws = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
    client = anthropic.Anthropic(default_headers={"anthropic-workspace-id": ws} if ws else None)
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        betas=["server-side-fallback-2026-07-01"],
        # On a policy decline, re-run on Anthropic's recommended fallback model.
        fallbacks="default",
        system=system,
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": user}],
    ) as stream:
        resp = stream.get_final_message()
    print(f"model usage: {resp.usage.input_tokens} in, {resp.usage.output_tokens} out")
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"model declined: {resp.stop_details}")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("model output hit max_tokens")
    return json.loads(next(b.text for b in resp.content if b.type == "text"))


def corpus(news: list[dict], research: list[dict], engagements: list[dict]) -> tuple[str, dict]:
    """Number every source; return the prompt text and an id -> source map."""
    index, lines = {}, []
    for n, x in enumerate(news, 1):
        sid = f"N{n}"
        index[sid] = {"kind": "news", **x}
        tag = f" [priority: {x['outlet']}]" if x.get("outlet") else ""
        if x.get("primary") or (x.get("section") or "").startswith("Congress.gov"):
            tag += f" [primary: {x.get('primary') or 'Congress.gov'}]"
        lines.append(f"{sid} | {x['date']} | {x.get('section') or ''} | {x.get('tag') or ''}{tag}\n"
                     f"   {x['headline']}\n   {x.get('body', '')}")
    for n, x in enumerate(research, 1):
        sid = f"R{n}"
        index[sid] = {"kind": "research", **x}
        by = f" | by {', '.join(x['authors'])}" if x.get("authors") else ""
        lines.append(f"{sid} | {x['date']} | CSIS{by}\n   {x['title']}\n   {x.get('summary') or '(title only)'}")
    for n, x in enumerate(engagements, 1):
        sid = f"E{n}"
        index[sid] = {"kind": "engagement", **x}
        fields = "; ".join(f"{k}: {v}" for k, v in x["fields"].items() if str(v).strip())
        lines.append(f"{sid} | {x['date']} | form submission\n   {fields}")
    return "\n".join(lines), index


def draft(news, research, engagements, window: str, style: str = "house") -> dict:
    text, index = corpus(news, research, engagements)
    user = f"Week covered: {window}.\nStyle: {STYLE[style]}\n\nSources:\n{text}"
    return resolve(ask(SYSTEM, user, SCHEMA), index)


def _clean(s: str) -> str:
    """Zero em-dashes in what ships; flagging the rest is the reviewer's job."""
    return re.sub(r"\s*—\s*", ", ", s or "").strip()


def _allowed(url: str) -> bool:
    """Heard on the Hill links only to .gov records, priority U.S. outlets and the approved list."""
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return host.endswith(".gov") or bool(config.outlet_for(host)) or any(
        host == d or host.endswith("." + d) for d in config.HILL_ALLOWED)


def _hill_rank(src: dict) -> int:
    """Congress.gov and committee releases first, then priority outlets by tier, then the rest."""
    if src.get("primary") or (src.get("section") or "").startswith("Congress.gov"):
        return 0
    return src.get("outlet_rank") or 99


def resolve(out: dict, index: dict) -> dict:
    """Replace source ids with links; drop anything uncited or off the approved source list."""
    copy = {"warnings": [], "heard_on_the_hill": [], "csis_impact": {"research": [], "engagements": []}}
    for it in out["heard_on_the_hill"][:5]:
        cands = [index[i] for i in [it["source_id"]] + list(it.get("context_ids") or [])
                 if i in index and index[i]["kind"] == "news"]
        cands = [c for c in cands if _allowed(c.get("url", ""))]
        if not cands:
            copy["warnings"].append(f"heard_on_the_hill: dropped {it['source_id']} (no source on the approved list)")
            continue
        src = min(cands, key=_hill_rank)       # link the primary record when there is one
        if len(it["headline"]) > 60:
            copy["warnings"].append(f"heard_on_the_hill: headline over 60 characters: {it['headline']}")
        copy["heard_on_the_hill"].append({"tag": it["tag"], "headline": _clean(it["headline"]),
                                          "body": _clean(it["body"]), "url": src.get("url", ""),
                                          "iso": src["date"]})
    seen = set()
    for it in out["csis_research"]:
        src = index.get(it["source_id"])
        if not src or src["kind"] != "research" or src["url"] in seen:
            continue
        seen.add(src["url"])
        copy["csis_impact"]["research"].append({
            "lead": ", ".join(src.get("authors") or []) or "CSIS", "title": src["title"],
            "line": _clean(it["line"]), "url": src["url"], "iso": src["date"]})
    for it in out["csis_engagements"]:
        src = index.get(it["source_id"])
        if not src or src["kind"] != "engagement" or not it["line"].strip():
            continue
        copy["csis_impact"]["engagements"].append({
            "lead": src.get("who", "") or "Engagement", "title": "", "line": _clean(it["line"]),
            "url": src.get("url", ""), "iso": src["date"]})
    return copy


def _span(s, e) -> str:
    if s == e:
        return f"{s.strftime('%B')} {s.day}"
    if s.month == e.month:
        return f"{s.strftime('%B')} {s.day}–{e.day}"
    return f"{s.strftime('%B')} {s.day} to {e.strftime('%B')} {e.day}"


def _md(iso: str) -> str:
    from datetime import date
    d = date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}"
