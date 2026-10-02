"""CSIS China Room Brief: issue dict -> table-based HTML email.

Layout follows the CSIS comms email template (the Pardot "Released This
Week" send): a grey preheader strip, a 600 x 200 banner, then the issue.
Inside, it borrows the China Daily Brief's parts so the two read as one
family: the black section bar with an accent ring, the left-ruled item
card, the date chip.

Two halves: The Week That Was (black bars) and The Week Ahead (navy bars).
An "In this issue" row under the date line jumps to each section.

Two modes. "draft" is the Monday-noon copy for review: human-owned sections
show their brief and the agent's candidate list. "final" is what goes out
Tuesday: an empty section is left out, never padded.
"""

from __future__ import annotations

import re

NAVY = "#004165"
NAVY_BRIGHT = "#0065A6"
BANNER_NAVY = "#0A2458"   # the comms template's navy
BACK_BAR = "#14181F"      # same black as the daily
AHEAD_BAR = NAVY
RING = "#EF4027"          # the daily's accent ring
INK = "#1A222E"
BODY = "#4A5260"
MUTE = "#6B7280"
RULE = "#E4E7EB"
SLOT_BG = "#F7F8FA"
SLOT_RULE = "#B8B0A3"
MONO = "'IBM Plex Mono',Consolas,'Courier New',monospace"
SERIF = "Georgia,'Times New Roman',serif"
SANS = "Arial,Helvetica,sans-serif"

_SEC = 'style="padding:20px 32px;border-bottom:1px solid #EBEBEB;" class="sec"'

# key, title, half
SECTIONS = [
    ("week_at_a_glance", "Week at a Glance", "ahead"),
    ("heard_on_the_hill", "Heard on the Hill", "back"),
    ("in_the_news", "In the News", "back"),
    ("research_roundup", "Research Roundup", "back"),
    ("in_the_works", "In the Works @ CSIS", "ahead"),
    ("on_the_horizon", "On the Horizon", "ahead"),
]


def esc(text) -> str:
    if text is None:
        return ""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def link(text: str, url: str, color: str = INK) -> str:
    if not url:
        return text
    return (f'<a href="{esc(url)}" style="color:{color};text-decoration:underline;'
            f'text-decoration-color:{NAVY_BRIGHT};text-underline-offset:3px;">{text}</a>')


def sec_bar(title: str, anchor: str, half: str) -> str:
    bg = AHEAD_BAR if half == "ahead" else BACK_BAR
    return (f'<a name="{anchor}" id="{anchor}"></a>'
            f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'class="sec-bar" style="background:{bg};margin-bottom:14px;">'
            f'<tr><td style="padding:9px 14px;">'
            f'<span style="font-family:{SANS};font-size:12px;color:{RING};line-height:1;'
            f'vertical-align:middle;margin-right:9px;">&#9679;</span>'
            f'<span style="font-family:{SANS};font-size:11px;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:2px;color:#FFFFFF;'
            f'vertical-align:middle;">{esc(title)}</span></td></tr></table>')


def part_head(label: str, dek: str) -> str:
    return (f'<div style="padding:26px 32px 4px;" class="sec">'
            f'<div style="font-family:{MONO};font-size:11px;font-weight:700;letter-spacing:2px;'
            f'text-transform:uppercase;color:{NAVY_BRIGHT};">{esc(label)}</div>'
            f'<div style="font-family:{SERIF};font-size:13px;color:{MUTE};margin-top:3px;'
            f'padding-bottom:8px;border-bottom:2px solid {NAVY};">{esc(dek)}</div></div>')


def axiom(label: str, text: str) -> str:
    return (f'<div style="font-family:{SERIF};font-size:13px;line-height:1.55;color:{BODY};margin-top:4px;">'
            f'<strong style="color:{INK};">{esc(label)}:</strong> {esc(text)}</div>')


def bullets(points: list[str]) -> str:
    if not points:
        return ""
    lis = "".join(f'<li style="margin:0 0 3px;">{esc(p)}</li>' for p in points)
    return (f'<ul style="margin:4px 0 0 18px;padding:0;font-family:{SERIF};font-size:13px;'
            f'line-height:1.5;color:{BODY};">{lis}</ul>')


def item(i: dict, rule: str = NAVY) -> str:
    tag_html = (f'<div style="font-family:{SANS};font-size:10px;color:{MUTE};'
                f'text-transform:uppercase;letter-spacing:1px;font-weight:600;'
                f'margin-bottom:2px;">{i["tag"]}</div>') if i.get("tag") else ""
    body = (f'<div style="font-family:{SERIF};font-size:13px;line-height:1.55;'
            f'color:{BODY};margin-top:3px;">{esc(i["body"])}</div>') if i.get("body") else ""
    why = axiom("Why it matters", i["why"]) if i.get("why") else ""
    return (f'<div style="margin-bottom:13px;padding-left:12px;border-left:3px solid {rule};">'
            f'{tag_html}<div style="font-family:{SERIF};font-size:14px;font-weight:700;'
            f'color:{INK};line-height:1.4;">{link(esc(i["headline"]), i.get("url", ""))}</div>'
            f'{body}{why}{bullets(i.get("bullets", []))}</div>')


def prose(text: str) -> str:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    return "".join(f'<p style="margin:0 0 10px;font-family:{SERIF};font-size:15px;'
                   f'line-height:1.6;color:{INK};">{esc(p)}</p>' for p in paras)


def slot(spec: str, candidates: list[dict] | None = None, note: str = "") -> str:
    """Draft-only: what the human writes here, and what the agent found for them."""
    rows = ""
    for c in candidates or []:
        meta = " &middot; ".join(esc(x) for x in (c.get("date_label"), c.get("source")) if x)
        rows += (f'<li style="margin:0 0 6px;">{link(esc(c["text"]), c.get("url", ""))}'
                 + (f'<span style="color:{MUTE};font-size:11px;"> &nbsp;{meta}</span>' if meta else "")
                 + '</li>')
    lst = (f'<ul style="margin:8px 0 0 18px;padding:0;font-family:{SERIF};font-size:13px;'
           f'line-height:1.45;color:{BODY};">{rows}</ul>') if rows else ""
    note_html = (f'<div style="font-family:{SERIF};font-size:13px;line-height:1.5;color:{BODY};'
                 f'margin-top:6px;">{note}</div>') if note else ""
    return (f'<div style="background:{SLOT_BG};border:1px dashed {SLOT_RULE};padding:12px 14px;">'
            f'<div style="font-family:{MONO};font-size:10px;font-weight:700;letter-spacing:1.5px;'
            f'text-transform:uppercase;color:{NAVY_BRIGHT};">For the coordinator</div>'
            f'<div style="font-family:{SANS};font-size:12px;color:{INK};margin-top:4px;">{esc(spec)}</div>'
            f'{note_html}{lst}</div>')


def calendar_row(month: str, day: str, headline: str, detail: str, url: str = "") -> str:
    chip = (f'<table cellpadding="0" cellspacing="0" border="0" style="background:{NAVY};">'
            f'<tr><td align="center" style="padding:4px 0 5px;width:52px;">'
            f'<div style="font-family:{SANS};font-size:10px;font-weight:700;letter-spacing:1.5px;'
            f'color:#FFFFFF;">{esc(month)}</div>'
            f'<div style="font-family:{SERIF};font-size:15px;font-weight:700;color:#FFFFFF;'
            f'line-height:1.1;">{esc(day)}</div></td></tr></table>')
    return (f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="border-bottom:1px solid {RULE};"><tr>'
            f'<td width="64" style="padding:9px 12px 9px 0;vertical-align:top;">{chip}</td>'
            f'<td style="padding:9px 0;vertical-align:top;">'
            f'<div style="font-family:{SERIF};font-size:14px;font-weight:700;color:{INK};">{link(esc(headline), url)}</div>'
            f'<div style="font-family:{SERIF};font-size:13px;line-height:1.45;color:{BODY};margin-top:3px;">{esc(detail)}</div>'
            f'</td></tr></table>')


def word_count(issue: dict) -> int:
    """Reader-facing words: section copy, not slots or chrome."""
    parts = [issue.get("editors_note", "")]
    for key, *_ in SECTIONS:
        for it in issue.get(key, {}).get("items", []):
            parts += [it.get("headline", ""), it.get("body", ""), it.get("detail", ""), it.get("why", "")]
            parts += it.get("bullets", [])
    return len(re.findall(r"[\w'’$%.,-]+", " ".join(parts)))


def render(issue: dict, mode: str = "final") -> str:
    draft = mode == "draft"
    wc = word_count(issue)
    mins = max(1, round(wc / 230))
    web_url, archive_url = issue.get("web_url", ""), issue.get("archive_url", "")
    out = []

    if draft:
        out.append(f'<div class="sec" style="background:#2E3644;padding:7px 32px;font-family:{SANS};font-size:10px;'
                   f'font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#C4C8CE;">'
                   f'Draft for review &middot; {esc(issue.get("draft_for", ""))}</div>')

    # Preheader strip, as in the CSIS comms template, with Read online / Past issues
    pill = (f'color:#4B4B4B;font-family:{SANS};font-size:10px;font-weight:700;text-decoration:underline;'
            f'margin-left:12px;')
    links = "".join(f'<a href="{esc(u)}" style="{pill}">{lbl}</a>'
                    for lbl, u in (("Read online", web_url), ("Past issues", archive_url)) if u)
    out.append(f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#E7E7E7;" '
               f'class="util-row"><tr><td class="util-cell" style="padding:10px 20px;font-family:Helvetica,{SANS};'
               f'font-size:10px;color:#4B4B4B;">China Room Brief: {esc(issue["date_line"])}</td>'
               f'<td class="util-cell" align="right" style="padding:10px 20px;white-space:nowrap;">{links}</td>'
               f'</tr></table>')

    # Banner. The cell is navy so the alt text still reads with images blocked.
    if issue.get("banner_src"):
        out.append(f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
                   f'<td bgcolor="{BANNER_NAVY}" style="background:{BANNER_NAVY};line-height:0;">'
                   f'<img src="{esc(issue["banner_src"])}" width="600" height="200" alt="CSIS China Room Brief" '
                   f'style="display:block;width:100%;max-width:600px;height:auto;border:0;color:#FFFFFF;'
                   f'font-family:{SERIF};font-size:28px;font-weight:700;line-height:1.2;"></td></tr></table>')

    # Date line, length, RE line
    re_html = (f'<div style="margin-top:10px;padding-top:10px;border-top:1px solid {RULE};font-size:13px;'
               f'color:{INK};font-family:{SERIF};line-height:1.55;"><strong style="font-size:11px;'
               f'letter-spacing:1.5px;font-family:{SANS};">RE:</strong>&nbsp; {esc(issue["re_line"])}</div>'
               ) if issue.get("re_line") else ""
    out.append(f'<div class="sec" style="padding:14px 32px;border-bottom:1px solid {RULE};">'
               f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
               f'<td class="mast-main" style="font-family:{SERIF};font-size:16px;color:{INK};">{esc(issue["date_line"])}</td>'
               f'<td class="mast-meta" align="right" style="font-family:{SANS};font-size:11px;color:{MUTE};white-space:nowrap;">'
               f'{esc(issue.get("issue_label", ""))} &middot; {wc:,} words &middot; {mins} min read</td>'
               f'</tr></table>{re_html}</div>')

    # In this issue
    present = [(k, t) for k, t, _ in SECTIONS
               if draft or issue.get(k, {}).get("items")]
    nav = " &nbsp;&middot;&nbsp; ".join(
        f'<a href="#{k}" style="color:{INK};text-decoration:none;">{esc(t)}</a>' for k, t in present)
    out.append(f'<div class="sec" style="padding:10px 32px;border-bottom:1px solid {RULE};font-family:{SANS};'
               f'font-size:11px;line-height:1.9;color:{INK};"><span style="font-size:10px;font-weight:700;'
               f'letter-spacing:1.5px;text-transform:uppercase;color:{MUTE};">In this issue &nbsp;</span>{nav}</div>')

    if issue.get("editors_note"):
        out.append(f'<div {_SEC}>{prose(issue["editors_note"])}</div>')
    elif draft:
        out.append(f'<div {_SEC}>{slot("Editor’s note: 60 to 100 words, the one thing to take from this week.")}</div>')

    def section(key):
        _, title, half = next(x for x in SECTIONS if x[0] == key)
        s = issue.get(key, {})
        if key in ("in_the_works", "on_the_horizon"):
            body = "".join(calendar_row(i["month"], i["day"], i["headline"], i.get("detail", ""), i.get("url", ""))
                           for i in s.get("items", []))
        else:
            rule = NAVY if half == "ahead" else BACK_BAR
            body = "".join(item(i, rule) for i in s.get("items", []))
        if draft and (not body or s.get("candidates") or s.get("gap")):
            body += slot(s.get("spec", ""), s.get("candidates"), s.get("gap", ""))
        if not body:
            return
        dek = (f'<div style="font-family:{SANS};font-size:10px;color:{MUTE};text-transform:uppercase;'
               f'letter-spacing:1px;margin:-6px 0 12px;">{esc(s["dek"])}</div>') if s.get("dek") else ""
        out.append(f'<div {_SEC}>{sec_bar(title, key, half)}{dek}{body}</div>')

    section("week_at_a_glance")
    out.append(part_head("The Week That Was", issue.get("back_window", "")))
    for k in ("heard_on_the_hill", "in_the_news", "research_roundup"):
        section(k)
    out.append(part_head("The Week Ahead", issue.get("ahead_window", "")))
    for k in ("in_the_works", "on_the_horizon"):
        section(k)

    c = issue.get("contact") or {}
    if c.get("email"):
        title = f', {esc(c["title"])},' if c.get("title") else ""
        out.append(f'<div class="sec" style="padding:20px 32px;border-bottom:1px solid {RULE};">'
                   f'<div style="font-family:{SANS};font-size:11px;font-weight:700;letter-spacing:1.5px;'
                   f'text-transform:uppercase;color:{INK};">Questions?</div>'
                   f'<div style="font-family:{SERIF};font-size:14px;line-height:1.6;color:{BODY};margin-top:4px;">'
                   f'Reach out to {esc(c.get("name", ""))}{title} at '
                   f'{link(esc(c["email"]), "mailto:" + c["email"], NAVY_BRIGHT)}.</div></div>')

    foot_links = " &nbsp;&middot;&nbsp; ".join(
        f'<a href="{esc(u)}" style="color:{MUTE};">{lbl}</a>'
        for lbl, u in (("Read online", web_url), ("Past issues", archive_url),
                       ("Full calendar", issue.get("calendar_url", ""))) if u)
    foot_links_html = f'<div style="margin-top:6px;">{foot_links}</div>' if foot_links else ""
    out.append(f'<div class="sec" style="padding:18px 32px 26px;font-family:{SANS};font-size:11px;'
               f'line-height:1.6;color:{MUTE};">{issue.get("footer", "")}{foot_links_html}</div>')

    body = "\n".join(out)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark"><meta name="supported-color-schemes" content="light dark">
<title>China Room Brief, {esc(issue["date_line"])}</title>
<style>
body {{ margin:0; padding:0; background:#EEF0F3; font-family:{SANS}; color:{INK}; -webkit-text-size-adjust:100%; }}
.container {{ width:600px; max-width:100%; margin:0 auto; background:#FFFFFF; }}
@media only screen and (max-width:600px) {{
  .sec {{ padding-left:16px !important; padding-right:16px !important; }}
  .util-row .util-cell {{ display:block !important; text-align:left !important; padding:6px 16px !important; }}
  .mast-main, .mast-meta {{ display:block !important; width:100% !important; text-align:left !important; }}
  .mast-meta {{ padding-top:4px !important; }}
}}
@media (prefers-color-scheme: dark) {{
  body {{ background:#121212 !important; }}
  .container {{ background:#1A1A1A !important; }}
  .container [style*="color:{INK}"] {{ color:#E8E6E1 !important; }}
  .container [style*="color:{BODY}"] {{ color:#C4C8CE !important; }}
  .container [style*="color:{MUTE}"] {{ color:#9AA3AE !important; }}
  .container [style*="color:{NAVY_BRIGHT}"] {{ color:#6FB1DE !important; }}
  .container [style*="background:{SLOT_BG}"] {{ background-color:#23272E !important; }}
}}
</style></head>
<body><div class="container">
{body}
</div></body></html>"""
