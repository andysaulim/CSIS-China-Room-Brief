"""CSIS China Room Brief: issue dict -> table-based HTML email.

Built from the China Daily Brief's house parts so the two read as one family:
the utility row, the masthead band, the black section bar with an accent ring,
the left-ruled item card, the date chip. What differs is the band colour (CSIS
navy, so a reader can tell the weekly from the daily at a glance), the title,
and the two-part spine: The Week That Was, then The Week Ahead.

Two modes. "draft" is the Monday-noon copy for review: human-owned sections
show their brief and the AI-pulled candidates the coordinator writes from.
"final" is what goes out Tuesday: an empty section is left out, never padded.
"""

from __future__ import annotations

import re
from datetime import date

NAVY = "#004165"        # masthead band, date chips
NAVY_DEEP = "#002147"
NAVY_BRIGHT = "#0065A6"  # links
BAR = "#14181F"          # section bar, same as the daily
RING = "#EF4027"         # the daily's accent ring
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


def esc(text) -> str:
    if text is None:
        return ""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def link(text: str, url: str) -> str:
    if not url:
        return text
    return (f'<a href="{esc(url)}" style="color:{INK};text-decoration:underline;'
            f'text-decoration-color:{NAVY_BRIGHT};text-underline-offset:3px;">{text}</a>')


def sec_bar(label: str, anchor: str) -> str:
    return (f'<a name="{anchor}" id="{anchor}"></a>'
            f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'class="sec-bar" style="background:{BAR};margin-bottom:14px;">'
            f'<tr><td style="padding:9px 14px;">'
            f'<span style="font-family:{SANS};font-size:12px;color:{RING};line-height:1;'
            f'vertical-align:middle;margin-right:9px;">&#9679;</span>'
            f'<span style="font-family:{SANS};font-size:11px;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:2px;color:#FFFFFF;'
            f'vertical-align:middle;">{label}</span></td></tr></table>')


def part_head(label: str, dek: str) -> str:
    """The divider between the two halves. Type and a hairline, not a band."""
    return (f'<div style="padding:26px 32px 4px;" class="sec">'
            f'<div style="font-family:{MONO};font-size:11px;font-weight:700;letter-spacing:2px;'
            f'text-transform:uppercase;color:{NAVY_BRIGHT};">{esc(label)}</div>'
            f'<div style="font-family:{SERIF};font-size:13px;color:{MUTE};margin-top:3px;'
            f'padding-bottom:8px;border-bottom:2px solid {NAVY};">{esc(dek)}</div></div>')


def item(tag: str, headline: str, url: str = "", body: str = "", rule: str = NAVY) -> str:
    tag_html = (f'<div style="font-family:{SANS};font-size:10px;color:{MUTE};'
                f'text-transform:uppercase;letter-spacing:1px;font-weight:600;'
                f'margin-bottom:2px;">{tag}</div>') if tag else ""
    body_html = (f'<div style="font-family:{SERIF};font-size:13px;line-height:1.55;'
                 f'color:{BODY};margin-top:3px;">{body}</div>') if body else ""
    return (f'<div style="margin-bottom:13px;padding-left:12px;border-left:3px solid {rule};">'
            f'{tag_html}<div style="font-family:{SERIF};font-size:14px;font-weight:700;'
            f'color:{INK};line-height:1.4;">{link(esc(headline), url)}</div>{body_html}</div>')


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
                 f'{"<span style=" + chr(39) + "color:" + MUTE + ";font-size:11px;" + chr(39) + "> &nbsp;" + meta + "</span>" if meta else ""}</li>')
    lst = (f'<ul style="margin:8px 0 0 18px;padding:0;font-family:{SERIF};font-size:13px;'
           f'line-height:1.45;color:{BODY};">{rows}</ul>') if rows else ""
    note_html = (f'<div style="font-family:{SERIF};font-size:13px;line-height:1.5;color:{BODY};'
                 f'margin-top:6px;">{note}</div>') if note else ""
    return (f'<div style="background:{SLOT_BG};border:1px dashed {SLOT_RULE};padding:12px 14px;">'
            f'<div style="font-family:{MONO};font-size:10px;font-weight:700;letter-spacing:1.5px;'
            f'text-transform:uppercase;color:{NAVY_BRIGHT};">For the coordinator</div>'
            f'<div style="font-family:{SANS};font-size:12px;color:{INK};margin-top:4px;">{esc(spec)}</div>'
            f'{note_html}{lst}</div>')


def date_chip(month: str, day: str) -> str:
    return (f'<table cellpadding="0" cellspacing="0" border="0" style="background:{NAVY};">'
            f'<tr><td align="center" style="padding:4px 0 5px;width:52px;">'
            f'<div style="font-family:{SANS};font-size:10px;font-weight:700;letter-spacing:1.5px;'
            f'color:#FFFFFF;">{esc(month)}</div>'
            f'<div style="font-family:{SERIF};font-size:15px;font-weight:700;color:#FFFFFF;'
            f'line-height:1.1;">{esc(day)}</div></td></tr></table>')


def calendar_row(month: str, day: str, headline: str, detail: str, url: str = "") -> str:
    return (f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="border-bottom:1px solid {RULE};"><tr>'
            f'<td width="64" style="padding:9px 12px 9px 0;vertical-align:top;">{date_chip(month, day)}</td>'
            f'<td style="padding:9px 0;vertical-align:top;">'
            f'<div style="font-family:{SERIF};font-size:14px;font-weight:700;color:{INK};">{link(esc(headline), url)}</div>'
            f'<div style="font-family:{SERIF};font-size:13px;line-height:1.45;color:{BODY};margin-top:3px;">{esc(detail)}</div>'
            f'</td></tr></table>')


def word_count(issue: dict) -> int:
    """Reader-facing words only: section copy, not slots or chrome."""
    parts = [issue.get("editors_note", "")]
    for k in ("week_at_a_glance", "heard_on_the_hill", "in_the_news",
              "research_roundup", "in_the_works", "on_the_horizon"):
        for it in issue.get(k, {}).get("items", []):
            parts += [it.get("headline", ""), it.get("body", ""), it.get("detail", "")]
    return len(re.findall(r"\b[\w'’$%.,-]+\b", " ".join(parts)))


def render(issue: dict, mode: str = "final") -> str:
    draft = mode == "draft"
    wc = word_count(issue)
    mins = max(1, round(wc / 230))
    out = []

    util_left = ("Draft for review &middot; " + esc(issue.get("draft_for", ""))) if draft else "CSIS"
    links = ""
    for label, url in (("Read online", issue.get("web_url")),
                       ("Full calendar", issue.get("calendar_url"))):
        if url:
            links += (f'<a href="{esc(url)}" style="display:inline-block;padding:6px 14px;margin:0 3px;'
                      f'font-family:{SANS};font-size:11px;font-weight:700;color:{BAR};background:#FFFFFF;'
                      f'text-decoration:none;white-space:nowrap;">{label}</a>')
    if draft or not issue.get("banner_src"):
        # The banner template opens on its own preheader strip; a second bar
        # above it in the sent copy would be chrome.
        out.append(f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
                   f'style="background:#2E3644;" class="util-row"><tr>'
                   f'<td class="util-cell" style="padding:7px 32px;font-family:{SANS};font-size:10px;'
                   f'font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#C4C8CE;">{util_left}</td>'
                   f'<td class="util-cell" align="right" style="padding:5px 32px 5px 0;">{links}</td></tr></table>')

    re_html = ("<div style='margin-top:10px;padding-top:10px;border-top:1px solid " + RULE + ";font-size:13px;"
               "color:" + INK + ";font-family:" + SERIF + ";line-height:1.55;'><strong style='font-size:11px;"
               "letter-spacing:1.5px;font-family:" + SANS + ";'>RE:</strong>&nbsp; " + esc(issue["re_line"]) + "</div>"
               ) if issue.get("re_line") else ""
    if issue.get("banner_src"):
        # The CSIS comms template (Released This Week, Pardot): grey preheader
        # strip, then a 600x200 banner in a #F4F4F4 cell. The banner is static
        # week to week, so date, length and RE line sit in a strip under it.
        # The cell is navy so the alt text still reads when images are blocked.
        out.append(f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#E7E7E7;">'
                   f'<tr><td class="sec" style="padding:10px 20px;font-family:Helvetica,{SANS};font-size:10px;'
                   f'color:#4B4B4B;">China Room Brief: {esc(issue["date_line"])}</td></tr></table>')
        out.append(f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
                   f'<td bgcolor="#0A2458" style="background:#0A2458;line-height:0;">'
                   f'<img src="{esc(issue["banner_src"])}" width="600" height="200" alt="CSIS China Room Brief" '
                   f'style="display:block;width:100%;max-width:600px;height:auto;border:0;color:#FFFFFF;'
                   f'font-family:{SERIF};font-size:28px;font-weight:700;line-height:1.2;"></td></tr></table>')
        out.append(f'<div class="sec" style="padding:14px 32px 14px;border-bottom:1px solid {RULE};">'
                   f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
                   f'<td style="font-family:{SERIF};font-size:16px;color:{INK};">{esc(issue["date_line"])}</td>'
                   f'<td align="right" style="font-family:{SANS};font-size:11px;color:{MUTE};white-space:nowrap;">'
                   f'{esc(issue.get("issue_label", ""))} &middot; {wc:,} words &middot; {mins} min read</td>'
                   f'</tr></table>{re_html}</div>')
    else:
            out.append(f'''<div style="background-color:{NAVY};color:#FFFFFF;padding:18px 32px 16px;" class="sec mast-band">
        <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
        <td class="mast-main" style="vertical-align:top;">
        <div style="font-family:{SANS};font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#C9D6E3;margin-bottom:7px;">CSIS China Room</div>
        <h1 style="margin:0 0 4px 0;font-size:26px;font-weight:700;font-family:{SERIF};color:#FFFFFF;letter-spacing:0.5px;">China Room Brief</h1>
        <div style="font-size:16px;color:#DCE4EC;font-family:{SERIF};">{esc(issue["date_line"])}</div>
        </td>
        <td class="mast-meta" style="vertical-align:bottom;text-align:right;">
        <div style="font-family:{SANS};font-size:11px;color:#C9D6E3;white-space:nowrap;">{esc(issue.get("issue_label", ""))}</div>
        <div style="font-family:{SANS};font-size:11px;color:#C9D6E3;white-space:nowrap;margin-top:3px;">{wc:,} words &middot; {mins} min read</div>
        </td></tr></table>
        {"<div style='margin-top:14px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.28);font-size:13px;color:#FFFFFF;font-family:" + SERIF + ";line-height:1.55;'><strong style='font-size:11px;letter-spacing:1.5px;font-family:" + SANS + ";'>RE:</strong>&nbsp; " + esc(issue["re_line"]) + "</div>" if issue.get("re_line") else ""}
</div>''')

    # Editor's note
    if issue.get("editors_note"):
        out.append(f'<div {_SEC}>{prose(issue["editors_note"])}</div>')
    elif draft:
        out.append(f'<div {_SEC}>{slot("Editor’s note: 60 to 80 words, first person plural, the one thing to take from this week.")}</div>')

    def section(key, title, render_items, spec=None):
        s = issue.get(key, {})
        body = render_items(s.get("items", [])) if s.get("items") else ""
        if draft and (not body or s.get("candidates") or s.get("gap")):
            body += slot(spec or s.get("spec", ""), s.get("candidates"), s.get("gap", ""))
        if not body:
            return
        dek = s.get("dek", "")
        dek_html = (f'<div style="font-family:{SANS};font-size:10px;color:{MUTE};text-transform:uppercase;'
                    f'letter-spacing:1px;margin:-8px 0 12px;">{esc(dek)}</div>') if dek else ""
        out.append(f'<div {_SEC}>{sec_bar(title, key)}{dek_html}{body}</div>')

    def items_html(items):
        return "".join(item(i.get("tag", ""), i["headline"], i.get("url", ""), esc(i.get("body", "")))
                       for i in items)

    def cal_html(items):
        return "".join(calendar_row(i["month"], i["day"], i["headline"], i.get("detail", ""), i.get("url", ""))
                       for i in items)

    section("week_at_a_glance", "Week at a Glance", items_html)

    out.append(part_head("The Week That Was", issue.get("back_window", "")))
    section("heard_on_the_hill", "Heard on the Hill", items_html)
    section("in_the_news", "In the News", items_html)
    section("research_roundup", "Research Roundup", items_html)

    out.append(part_head("The Week Ahead", issue.get("ahead_window", "")))
    section("in_the_works", "In the Works @ CSIS", cal_html)
    section("on_the_horizon", "On the Horizon", cal_html)

    foot = issue.get("footer", "")
    out.append(f'<div style="padding:18px 32px 26px;font-family:{SANS};font-size:11px;line-height:1.6;'
               f'color:{MUTE};" class="sec">{foot}</div>')

    body = "\n".join(out)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark"><meta name="supported-color-schemes" content="light dark">
<title>China Room Brief</title>
<style>
body {{ margin:0; padding:0; background:#EEF0F3; font-family:{SANS}; color:{INK}; -webkit-text-size-adjust:100%; }}
.container {{ width:600px; max-width:100%; margin:0 auto; background:#FFFFFF; }}
@media only screen and (max-width:600px) {{
  .sec {{ padding-left:16px !important; padding-right:16px !important; }}
  .util-row .util-cell {{ display:block !important; text-align:center !important; padding:5px 8px !important; }}
  .mast-main, .mast-meta {{ display:block !important; width:100% !important; }}
  .mast-meta {{ text-align:left !important; padding-top:10px !important; }}
  h1 {{ font-size:22px !important; }}
}}
@media (prefers-color-scheme: dark) {{
  body {{ background:#121212 !important; }}
  .container {{ background:#1A1A1A !important; }}
  .container [style*="color:{INK}"] {{ color:#E8E6E1 !important; }}
  .container [style*="color:{BODY}"] {{ color:#C4C8CE !important; }}
  .container [style*="color:{MUTE}"] {{ color:#9AA3AE !important; }}
  .container [style*="color:{NAVY_BRIGHT}"] {{ color:#6FB1DE !important; }}
  .container [style*="background:{SLOT_BG}"] {{ background-color:#23272E !important; }}
  .container a {{ color:#E8E6E1 !important; }}
}}
</style></head>
<body><div class="container">
{body}
</div></body></html>"""
