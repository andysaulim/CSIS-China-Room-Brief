"""CSIS China Room Brief: issue dict -> table-based HTML email.

Built from the China Daily Brief's house parts so the two read as one family:
the section bar with an accent ring, the left-ruled item card, the date chip.
The masthead is a newspaper nameplate in live type, so it needs no hosted
image and survives clients that block images.

Two halves, told apart by the bar colour: The Week That Was runs on black
bars, The Week Ahead on navy. Every section bar carries a one-line dek saying
what the section is, and an "In this issue" row under the nameplate jumps to
each one.

Two modes. "draft" is the Monday-noon copy for review: human-owned sections
show their brief and the agent's candidate list. "final" is what goes out
Tuesday: an empty section is left out, never padded.
"""

from __future__ import annotations

import re

NAVY = "#004165"
NAVY_BRIGHT = "#0065A6"
BACK_BAR = "#14181F"      # The Week That Was, same black as the daily
AHEAD_BAR = NAVY          # The Week Ahead
BACK_RING = "#EF4027"     # the daily's accent ring
AHEAD_RING = "#6FB1DE"
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

# key, title, half, dek
SECTIONS = [
    ("week_at_a_glance", "Week at a Glance", "lede", "Three things to watch in US-China relations this week"),
    ("heard_on_the_hill", "Heard on the Hill", "back", "What Congress said and did on China"),
    ("in_the_news", "In the News", "back", "The China story that led US coverage"),
    ("research_roundup", "Research Roundup", "back", "New work from other research institutions and CRS"),
    ("in_the_works", "In the Works @ CSIS", "ahead", "What CSIS scholars have coming"),
    ("on_the_horizon", "On the Horizon", "ahead", "Dates on the calendar"),
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


def sec_bar(title: str, anchor: str, half: str, dek: str) -> str:
    bg, ring = (AHEAD_BAR, AHEAD_RING) if half == "ahead" else (BACK_BAR, BACK_RING)
    return (f'<a name="{anchor}" id="{anchor}"></a>'
            f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'class="sec-bar" style="background:{bg};"><tr><td style="padding:10px 14px;">'
            f'<span style="font-family:{SANS};font-size:12px;color:{ring};line-height:1;'
            f'vertical-align:middle;margin-right:9px;">&#9679;</span>'
            f'<span style="font-family:{SANS};font-size:13px;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:2px;color:#FFFFFF;'
            f'vertical-align:middle;">{esc(title)}</span></td></tr></table>'
            f'<div style="font-family:{SERIF};font-size:13px;font-style:italic;color:{MUTE};'
            f'margin:7px 0 14px;">{esc(dek)}</div>')


def part_head(label: str, dek: str, half: str) -> str:
    color = NAVY if half == "ahead" else BACK_BAR
    return (f'<div style="padding:28px 32px 2px;" class="sec">'
            f'<div style="font-family:{SERIF};font-size:22px;font-weight:700;color:{color};">{esc(label)}</div>'
            f'<div style="font-family:{SANS};font-size:11px;letter-spacing:1px;text-transform:uppercase;'
            f'color:{MUTE};margin-top:4px;padding-bottom:9px;border-bottom:2px solid {color};">{esc(dek)}</div></div>')


def axiom(label: str, text: str) -> str:
    """A Smart Brevity signpost: bold label, then one plain sentence."""
    return (f'<div style="font-family:{SERIF};font-size:15px;line-height:1.6;color:{INK};margin-top:6px;">'
            f'<strong style="font-family:{SANS};font-size:14px;">{esc(label)}:</strong> {esc(text)}</div>')


def bullets(points: list[str]) -> str:
    if not points:
        return ""
    lis = "".join(f'<li style="margin:0 0 5px;">{esc(p)}</li>' for p in points)
    return (f'<ul style="margin:6px 0 0 18px;padding:0;font-family:{SERIF};font-size:15px;'
            f'line-height:1.55;color:{INK};">{lis}</ul>')


def item(i: dict, rule: str = NAVY) -> str:
    """Headline, a one-sentence lede, Why it matters, then bullets."""
    tag_html = (f'<div style="font-family:{SANS};font-size:10px;color:{MUTE};'
                f'text-transform:uppercase;letter-spacing:1px;font-weight:600;'
                f'margin-bottom:2px;">{i["tag"]}</div>') if i.get("tag") else ""
    lede = (f'<div style="font-family:{SERIF};font-size:15px;line-height:1.6;color:{INK};margin-top:4px;">'
            f'{esc(i["body"])}</div>') if i.get("body") else ""
    why = axiom("Why it matters", i["why"]) if i.get("why") else ""
    return (f'<div style="margin-bottom:18px;padding-left:12px;border-left:3px solid {rule};">'
            f'{tag_html}<div style="font-family:{SERIF};font-size:17px;font-weight:700;'
            f'color:{INK};line-height:1.35;">{link(esc(i["headline"]), i.get("url", ""))}</div>'
            f'{lede}{why}{bullets(i.get("bullets", []))}</div>')


def prose(text: str, size: int = 15) -> str:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    return "".join(f'<p style="margin:0 0 11px;font-family:{SERIF};font-size:{size}px;'
                   f'line-height:1.65;color:{INK};">{esc(p)}</p>' for p in paras)


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
    return (f'<div style="background:{SLOT_BG};border:1px dashed {SLOT_RULE};padding:12px 14px;margin-top:6px;">'
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
            f'<div style="font-family:{SERIF};font-size:15px;font-weight:700;color:{INK};">{link(esc(headline), url)}</div>'
            f'<div style="font-family:{SERIF};font-size:13px;line-height:1.5;color:{BODY};margin-top:3px;">{esc(detail)}</div>'
            f'</td></tr></table>')


def lead_story(lead: dict) -> str:
    """In the News: one story, the one the most priority outlets carried."""
    cov = ""
    for c in lead.get("coverage", []):
        cov += (f'<tr><td style="padding:7px 10px 7px 0;vertical-align:top;width:128px;font-family:{SANS};'
                f'font-size:11px;font-weight:700;color:{INK};text-transform:uppercase;letter-spacing:0.5px;'
                f'border-bottom:1px solid {RULE};">'
                f'{esc(c["outlet"])}<div style="font-weight:400;color:{MUTE};text-transform:none;'
                f'letter-spacing:0;margin-top:1px;">{esc(c.get("date", ""))}</div></td>'
                f'<td style="padding:7px 0;vertical-align:top;font-family:{SERIF};font-size:14px;'
                f'line-height:1.45;color:{INK};border-bottom:1px solid {RULE};">'
                f'{link(esc(c["headline"]), c.get("url", ""))}</td></tr>')
    cov_html = (f'<div style="font-family:{SANS};font-size:10px;font-weight:700;letter-spacing:1.5px;'
                f'text-transform:uppercase;color:{NAVY_BRIGHT};margin:16px 0 2px;">How it was covered</div>'
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0">{cov}</table>') if cov else ""
    kicker = (f'<div style="font-family:{SANS};font-size:10px;font-weight:700;letter-spacing:1.5px;'
              f'text-transform:uppercase;color:{MUTE};margin-bottom:6px;">{esc(lead.get("kicker", ""))}</div>'
              ) if lead.get("kicker") else ""
    parts = prose(lead.get("body", ""))
    if lead.get("why"):
        parts += axiom("Why it matters", lead["why"])
    if lead.get("driving"):
        parts += (f'<div style="font-family:{SANS};font-size:14px;font-weight:700;color:{INK};margin-top:12px;">'
                  f'Driving the news:</div>' + bullets(lead["driving"]))
    if lead.get("between"):
        parts += axiom("Between the lines", lead["between"])
    return (f'{kicker}<div style="font-family:{SERIF};font-size:22px;font-weight:700;line-height:1.3;'
            f'color:{INK};margin-bottom:10px;">{esc(lead["headline"])}</div>'
            f'{parts}{cov_html}')


def also_list(items: list[dict]) -> str:
    if not items:
        return ""
    rows = "".join(
        f'<li style="margin:0 0 7px;">{link(esc(i["headline"]), i.get("url", ""))}'
        f'<span style="color:{MUTE};font-family:{SANS};font-size:11px;"> &nbsp;{i.get("tag", "")}</span></li>'
        for i in items)
    return (f'<div style="font-family:{SANS};font-size:10px;font-weight:700;letter-spacing:1.5px;'
            f'text-transform:uppercase;color:{NAVY_BRIGHT};margin:20px 0 6px;">Also in the news</div>'
            f'<ul style="margin:0 0 0 18px;padding:0;font-family:{SERIF};font-size:14px;line-height:1.45;'
            f'color:{INK};">{rows}</ul>')


def word_count(issue: dict) -> int:
    """Reader-facing words: section copy, not slots or chrome."""
    parts = [issue.get("editors_note", ""), issue.get("bottom_line", "")]
    for key, *_ in SECTIONS:
        s = issue.get(key, {})
        parts.append(s.get("big_picture", ""))
        for it in s.get("items", []) + s.get("also", []):
            parts += [it.get("headline", ""), it.get("body", ""), it.get("detail", ""), it.get("why", "")]
            parts += it.get("bullets", [])
        lead = s.get("lead") or {}
        parts += [lead.get("headline", ""), lead.get("body", ""), lead.get("why", ""), lead.get("between", "")]
        parts += lead.get("driving", [])
        parts += [c.get("headline", "") for c in lead.get("coverage", [])]
    return len(re.findall(r"[\w'’$%.,-]+", " ".join(parts)))


def _has_content(s: dict) -> bool:
    return bool(s.get("items") or s.get("lead"))


def render(issue: dict, mode: str = "final") -> str:
    draft = mode == "draft"
    wc = word_count(issue)
    mins = max(1, round(wc / 230))
    web_url, archive_url = issue.get("web_url", ""), issue.get("archive_url", "")
    out = []

    # Utility row: draft status, Read online, Past issues
    a = (f'color:{INK};font-family:{SANS};font-size:11px;font-weight:700;text-decoration:none;'
         f'margin-left:14px;')
    links = "".join(f'<a href="{esc(u)}" style="{a}">{lbl}</a>'
                    for lbl, u in (("Read online", web_url), ("Past issues", archive_url)) if u)
    left = (f'<span style="font-family:{MONO};font-size:10px;font-weight:700;letter-spacing:1.5px;'
            f'text-transform:uppercase;color:#B52B2B;">Draft for review &middot; {esc(issue.get("draft_for", ""))}</span>'
            ) if draft else ""
    if links or left:
        out.append(f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#F1F2F4;" '
                   f'class="util-row"><tr><td class="util-cell sec" style="padding:8px 32px;">{left}</td>'
                   f'<td class="util-cell sec" align="right" style="padding:8px 32px;white-space:nowrap;">{links}</td>'
                   f'</tr></table>')

    # Nameplate
    re_html = (f'<div style="margin-top:10px;font-size:13px;color:{INK};font-family:{SERIF};line-height:1.55;">'
               f'<strong style="font-size:11px;letter-spacing:1.5px;font-family:{SANS};">RE:</strong>&nbsp; '
               f'{esc(issue["re_line"])}</div>') if issue.get("re_line") else ""
    out.append(f'<div class="sec" style="padding:18px 32px 0;">'
               f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
               f'<td class="mast-main" style="font-family:{SANS};font-size:11px;color:{INK};">'
               f'<strong style="letter-spacing:1.5px;">CSIS</strong>'
               f'<span style="color:{MUTE};"> &nbsp;Center for Strategic and International Studies</span></td>'
               f'<td class="mast-meta" align="right" style="font-family:{SANS};font-size:11px;color:{MUTE};white-space:nowrap;">'
               f'{esc(issue.get("issue_label", ""))}</td></tr></table>'
               f'<h1 style="margin:16px 0 12px;font-family:{SERIF};font-size:44px;font-weight:700;'
               f'letter-spacing:-0.6px;line-height:1;color:{INK};">China Room Brief</h1>'
               f'<div style="height:2px;border-top:3px solid {NAVY};border-bottom:1px solid {NAVY};"></div>'
               f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:8px;"><tr>'
               f'<td style="font-family:{SERIF};font-size:15px;color:{INK};">{esc(issue["date_line"])}</td>'
               f'<td align="right" style="font-family:{SANS};font-size:11px;color:{MUTE};white-space:nowrap;">'
               f'{wc:,} words &middot; {mins} min read</td></tr></table>{re_html}</div>')

    # In this issue
    present = [(k, t) for k, t, *_ in SECTIONS if draft or _has_content(issue.get(k, {}))]
    nav = " &nbsp;&middot;&nbsp; ".join(
        f'<a href="#{k}" style="color:{INK};text-decoration:none;">{esc(t)}</a>' for k, t in present)
    out.append(f'<div class="sec" style="padding:12px 32px 14px;border-bottom:1px solid {RULE};'
               f'font-family:{SANS};font-size:12px;line-height:1.9;color:{INK};">'
               f'<span style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;'
               f'color:{MUTE};">In this issue &nbsp;</span>{nav}</div>')

    # Editor's note
    if issue.get("editors_note"):
        out.append(f'<div {_SEC}>{prose(issue["editors_note"])}</div>')
    elif draft:
        out.append(f'<div {_SEC}>{slot("Editor’s note: 60 to 100 words, the one thing to take from this week.")}</div>')

    def section(key):
        _, title, half, dek = next(x for x in SECTIONS if x[0] == key)
        s = issue.get(key, {})
        if s.get("lead"):
            body = lead_story(s["lead"]) + also_list(s.get("also", []))
        elif key in ("in_the_works", "on_the_horizon"):
            body = "".join(calendar_row(i["month"], i["day"], i["headline"], i.get("detail", ""), i.get("url", ""))
                           for i in s.get("items", []))
        else:
            rule = NAVY if half != "back" else BACK_BAR
            body = "".join(item(i, rule) for i in s.get("items", []))
        if s.get("big_picture") and body:
            body = (f'<div style="margin:0 0 16px;">{axiom("The big picture", s["big_picture"])}</div>') + body
        if draft and (not body or s.get("candidates") or s.get("gap")):
            body += slot(s.get("spec", ""), s.get("candidates"), s.get("gap", ""))
        if body:
            out.append(f'<div {_SEC}>{sec_bar(title, key, "ahead" if half == "lede" else half, dek)}{body}</div>')

    section("week_at_a_glance")
    out.append(part_head("The Week That Was", issue.get("back_window", ""), "back"))
    for k in ("heard_on_the_hill", "in_the_news", "research_roundup"):
        section(k)
    out.append(part_head("The Week Ahead", issue.get("ahead_window", ""), "ahead"))
    for k in ("in_the_works", "on_the_horizon"):
        section(k)

    if issue.get("bottom_line"):
        out.append(f'<div {_SEC}>{axiom("The bottom line", issue["bottom_line"])}</div>')

    # Contact
    c = issue.get("contact") or {}
    if c.get("email"):
        title = f', {esc(c["title"])},' if c.get("title") else ""
        out.append(f'<div class="sec" style="padding:22px 32px;border-top:2px solid {NAVY};">'
                   f'<div style="font-family:{SERIF};font-size:16px;font-weight:700;color:{INK};">Questions?</div>'
                   f'<div style="font-family:{SERIF};font-size:14px;line-height:1.6;color:{BODY};margin-top:4px;">'
                   f'Reach out to {esc(c.get("name", ""))}{title} at '
                   f'{link(esc(c["email"]), "mailto:" + c["email"], NAVY_BRIGHT)}.</div></div>')

    foot_links = " &nbsp;&middot;&nbsp; ".join(
        f'<a href="{esc(u)}" style="color:{MUTE};">{lbl}</a>'
        for lbl, u in (("Read online", web_url), ("Past issues", archive_url),
                       ("Full calendar", issue.get("calendar_url", ""))) if u)
    foot_links_html = f'<div style="margin-top:6px;">{foot_links}</div>' if foot_links else ""
    out.append(f'<div class="sec" style="padding:16px 32px 26px;background:#F7F8FA;font-family:{SANS};font-size:11px;'
               f'line-height:1.6;color:{MUTE};">{issue.get("footer", "")}{foot_links_html}</div>')

    body = "\n".join(out)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark"><meta name="supported-color-schemes" content="light dark">
<title>China Room Brief, {esc(issue["date_line"])}</title>
<style>
body {{ margin:0; padding:0; background:#EEF0F3; font-family:{SANS}; color:{INK}; -webkit-text-size-adjust:100%; }}
.container {{ width:640px; max-width:100%; margin:0 auto; background:#FFFFFF; }}
@media only screen and (max-width:600px) {{
  .sec {{ padding-left:16px !important; padding-right:16px !important; }}
  .util-row .util-cell {{ display:block !important; text-align:left !important; padding:4px 16px !important; }}
  .mast-main, .mast-meta {{ display:block !important; width:100% !important; text-align:left !important; }}
  h1 {{ font-size:34px !important; }}
}}
@media (prefers-color-scheme: dark) {{
  body {{ background:#121212 !important; }}
  .container {{ background:#1A1A1A !important; }}
  .container [style*="color:{INK}"] {{ color:#E8E6E1 !important; }}
  .container [style*="color:{BODY}"] {{ color:#C4C8CE !important; }}
  .container [style*="color:{MUTE}"] {{ color:#9AA3AE !important; }}
  .container [style*="color:{NAVY_BRIGHT}"] {{ color:#6FB1DE !important; }}
  .container [style*="color:{BACK_BAR}"] {{ color:#E8E6E1 !important; }}
  .container [style*="color:{NAVY}"] {{ color:#6FB1DE !important; }}
  .container [style*="background:{SLOT_BG}"], .container [style*="background:#F1F2F4"] {{ background-color:#23272E !important; }}
}}
</style></head>
<body><div class="container">
{body}
</div></body></html>"""
