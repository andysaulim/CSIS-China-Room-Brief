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
BANNER_NAVY = "#001F59"   # sampled from the CSIS comms banner
BACK_BAR = "#14181F"      # same black as the daily
AHEAD_BAR = NAVY
INK = "#1A222E"
BODY = "#4A5260"
MUTE = "#6B7280"
RULE = "#E4E7EB"
SLOT_BG = "#F7F8FA"
SLOT_RULE = "#B8B0A3"
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


TOC = {
    "week_at_a_glance": "Three things to watch next week",
    "heard_on_the_hill": "What Congress said and did on China",
    "in_the_news": "The week's top five China stories",
    "research_roundup": "New work from other think tanks and CRS",
    "in_the_works": "What CSIS scholars have coming",
    "on_the_horizon": "Key dates ahead",
}


def esc(text) -> str:
    if text is None:
        return ""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def link(text: str, url: str, color: str = INK) -> str:
    if not url:
        return text
    return f'<a href="{esc(url)}" style="color:{color};text-decoration:none;">{text}</a>'


def sec_bar(title: str, anchor: str, half: str) -> str:
    """Edge-to-edge section banner in the masthead navy."""
    return (f'<a name="{anchor}" id="{anchor}"></a>'
            f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'class="sec-bar" style="background:{BANNER_NAVY};">'
            f'<tr><td class="sec" style="padding:11px 32px;font-family:{SANS};font-size:13px;font-weight:700;'
            f'letter-spacing:1px;text-transform:uppercase;color:#FFFFFF;">{esc(title)}</td></tr></table>')


def part_head(label: str, dek: str) -> str:
    return (f'<div style="padding:28px 32px 12px;" class="sec">'
            f'<span style="font-family:{SERIF};font-size:20px;font-weight:700;color:{INK};">{esc(label)}</span>'
            f'<span style="font-family:{SANS};font-size:12px;color:{MUTE};"> &nbsp;{esc(dek)}</span></div>')


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
    tag_html = (f'<div style="font-family:{SANS};font-size:11px;font-weight:700;color:{MUTE};'
                f'margin-bottom:3px;">{i["tag"]}</div>') if i.get("tag") else ""
    body = (f'<div style="font-family:{SERIF};font-size:14px;line-height:1.6;'
            f'color:{BODY};margin-top:4px;">{esc(i["body"])}</div>') if i.get("body") else ""
    why = axiom("Why it matters", i["why"]) if i.get("why") else ""
    return (f'<div style="padding:12px 0 14px;border-top:1px solid {RULE};">'
            f'{tag_html}<div style="font-family:{SERIF};font-size:16px;font-weight:700;'
            f'color:{INK};line-height:1.35;">{link(esc(i["headline"]), i.get("url", ""))}</div>'
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
            f'<div style="font-family:{SANS};font-size:12px;font-weight:700;color:{NAVY};">For the coordinator</div>'
            f'<div style="font-family:{SANS};font-size:12px;color:{INK};margin-top:4px;">{esc(spec)}</div>'
            f'{note_html}{lst}</div>')


def news_row(n: int, i: dict) -> str:
    """In the News: ranked, larger type, a summary under each headline."""
    why = axiom("Why it matters", i["why"]) if i.get("why") else ""
    body = (f'<div style="font-family:{SERIF};font-size:15px;line-height:1.6;color:{BODY};margin-top:6px;">'
            f'{esc(i["body"])}</div>') if i.get("body") else ""
    return (f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top:1px solid {RULE};"><tr>'
            f'<td width="44" style="padding:16px 0 16px;vertical-align:top;font-family:{SERIF};font-size:30px;'
            f'font-weight:700;line-height:1;color:{NAVY};">{n}</td>'
            f'<td style="padding:16px 0;vertical-align:top;">'
            f'<div style="font-family:{SANS};font-size:11px;color:{MUTE};font-weight:700;margin-bottom:4px;">{i.get("tag", "")}</div>'
            f'<div style="font-family:{SERIF};font-size:19px;font-weight:700;line-height:1.3;color:{INK};">'
            f'{link(esc(i["headline"]), i.get("url", ""))}</div>{body}{why}</td></tr></table>')


def agenda(items: list[dict], meta_first: bool = False) -> str:
    """A printed-agenda calendar: month headings, then one row per date with
    the day, the item, and its place or program set right."""
    html, current = "", None
    for i in items:
        g = i.get("group", "")
        if g != current:
            current = g
            html += (f'<div style="font-family:{SERIF};font-size:15px;font-weight:700;color:{NAVY};margin:{"0" if not html else "18px"} 0 0;'
                     f'padding-bottom:6px;border-bottom:2px solid {NAVY};">{esc(g)}</div>')
        day = i.get("day") or ""
        size = "17px" if day[:1].isdigit() else "12px"
        detail = (f'<div style="font-family:{SERIF};font-size:13px;line-height:1.5;color:{BODY};margin-top:3px;">'
                  f'{esc(i["detail"])}</div>') if i.get("detail") else ""
        meta = (f'<div class="cal-meta" style="font-family:{SANS};font-size:12px;color:{MUTE};margin-top:3px;">{esc(i.get("kind", ""))}</div>') if i.get("kind") else ""
        html += (f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
                 f'style="border-bottom:1px solid {RULE};"><tr>'
                 f'<td width="60" style="padding:11px 10px 11px 0;vertical-align:top;font-family:{SERIF};'
                 f'font-size:{size};font-weight:700;line-height:1.2;color:{NAVY};white-space:nowrap;">{esc(day)}</td>'
                 f'<td style="padding:11px 0;vertical-align:top;">'
                 f'<div style="font-family:{SERIF};font-size:15px;font-weight:700;line-height:1.35;color:{INK};">'
                 f'{link(esc(i["headline"]), i.get("url", ""))}</div>{meta}{detail}</td></tr></table>')
    return html


def research_row(i: dict) -> str:
    """Institution in its own column, so a reader sees who wrote what at a glance."""
    return (f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top:1px solid {RULE};"><tr>'
            f'<td width="128" class="r-inst" style="padding:12px 14px 12px 0;vertical-align:top;">'
            f'<div style="font-family:{SANS};font-size:13px;font-weight:700;line-height:1.35;color:{NAVY};">{esc(i["institution"])}</div>'
            f'<div style="font-family:{SANS};font-size:11px;color:{MUTE};margin-top:3px;">{esc(i.get("date", ""))}</div></td>'
            f'<td style="padding:12px 0;vertical-align:top;">'
            f'<div style="font-family:{SERIF};font-size:15px;font-weight:700;line-height:1.35;color:{INK};">'
            f'{link(esc(i["headline"]), i.get("url", ""))}</div>'
            f'<div style="font-family:{SERIF};font-size:13px;line-height:1.5;color:{BODY};margin-top:3px;">{esc(i.get("body", ""))}</div>'
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

    label = "For internal use only"
    if draft:
        label += f' &nbsp;&middot;&nbsp; <span style="color:#FFB4A8;">Draft for review &middot; {esc(issue.get("draft_for", ""))}</span>'
    out.append(f'<div class="sec" style="background:{BANNER_NAVY};padding:8px 20px;font-family:{SANS};font-size:10px;'
               f'font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#C9D6E3;">{label}</div>')

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
    out.append(f'<div class="sec" style="padding:14px 32px;border-bottom:1px solid {RULE};">'
               f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
               f'<td class="mast-main" style="font-family:{SERIF};font-size:16px;color:{INK};">{esc(issue["date_line"])}</td>'
               f'<td class="mast-meta" align="right" style="font-family:{SANS};font-size:11px;color:{MUTE};white-space:nowrap;">'
               f'{esc(issue.get("issue_label", ""))} &middot; {wc:,} words &middot; {mins} min read</td>'
               f'</tr></table></div>')

    # In this issue: one row per section, name and what it holds
    present = [(k, t) for k, t, _ in SECTIONS if draft or issue.get(k, {}).get("items")]
    rows = "".join(
        f'<tr><td style="padding:5px 16px 5px 0;white-space:nowrap;vertical-align:top;">'
        f'<a href="#{k}" style="font-family:{SANS};font-size:13px;font-weight:700;color:{INK};text-decoration:none;">{esc(t)}</a></td>'
        f'<td style="padding:5px 0;vertical-align:top;font-family:{SERIF};font-size:13px;color:{BODY};">{esc(TOC.get(k, ""))}</td></tr>'
        for k, t in present)
    out.append(f'<div class="sec" style="padding:16px 32px 14px;border-bottom:1px solid {RULE};">'
               f'<div style="font-family:{SERIF};font-size:15px;font-weight:700;color:{INK};margin-bottom:6px;">In this issue</div>'
               f'<table cellpadding="0" cellspacing="0" border="0">{rows}</table></div>')

    if issue.get("editors_note"):
        out.append(f'<div {_SEC}>{prose(issue["editors_note"])}</div>')
    elif draft:
        out.append(f'<div {_SEC}>{slot("Editor’s note: 60 to 100 words, the one thing to take from this week.")}</div>')

    def section(key):
        _, title, half = next(x for x in SECTIONS if x[0] == key)
        s = issue.get(key, {})
        if key in ("in_the_works", "on_the_horizon"):
            body = agenda(s.get("items", []))
        elif key == "in_the_news":
            body = "".join(news_row(n, i) for n, i in enumerate(s.get("items", []), 1))
        elif key == "research_roundup" and s.get("items") and "institution" in s["items"][0]:
            body = "".join(research_row(i) for i in s["items"])
        else:
            rule = NAVY if half == "ahead" else BACK_BAR
            body = "".join(item(i, rule) for i in s.get("items", []))
        # no rule between the section banner and its first item
        body = body.replace(f"border-top:1px solid {RULE};", "", 1)
        if draft and (not body or s.get("candidates") or s.get("gap")):
            body += slot(s.get("spec", ""), s.get("candidates"), s.get("gap", ""))
        if not body:
            return
        dek = ""
        out.append(f'{sec_bar(title, key, half)}'
                   f'<div class="sec" style="padding:16px 32px 22px;border-bottom:1px solid #EBEBEB;">{dek}{body}</div>')

    section("week_at_a_glance")
    out.append(part_head("The Week That Was", issue.get("back_window", "")))
    for k in ("heard_on_the_hill", "in_the_news", "research_roundup"):
        section(k)
    out.append(part_head("The Week Ahead", issue.get("ahead_window", "")))
    for k in ("in_the_works", "on_the_horizon"):
        section(k)

    # Bottom banner, in the top banner's navy: contact, links, provenance.
    c = issue.get("contact") or {}
    contact = ""
    if c.get("email"):
        title = f', {esc(c["title"])},' if c.get("title") else ""
        contact = (f'<div style="font-family:{SERIF};font-size:18px;font-weight:700;color:#FFFFFF;">Questions?</div>'
                   f'<div style="font-family:{SERIF};font-size:14px;line-height:1.6;color:#DCE4EC;margin-top:4px;">'
                   f'Reach out to {esc(c.get("name", ""))}{title} at '
                   f'<a href="mailto:{esc(c["email"])}" style="color:#FFFFFF;text-decoration:underline;">{esc(c["email"])}</a>.</div>')
    foot_links = " &nbsp;&middot;&nbsp; ".join(
        f'<a href="{esc(u)}" style="color:#FFFFFF;">{lbl}</a>'
        for lbl, u in (("Read online", web_url), ("Past issues", archive_url),
                       ("Full calendar", issue.get("calendar_url", ""))) if u)
    out.append(f'<div class="sec bottom-band" style="background:{BANNER_NAVY};padding:26px 32px 28px;">{contact}'
               f'<div style="height:1px;background:rgba(255,255,255,0.22);margin:18px 0 12px;"></div>'
               f'<div style="font-family:{SANS};font-size:11px;line-height:1.7;color:#9FB2C8;">'
               f'<strong style="color:#FFFFFF;letter-spacing:1.5px;">CSIS</strong> &nbsp;Center for Strategic and International Studies'
               f'{"<br>" + issue.get("footer", "") if issue.get("footer") else ""}'
               f'{"<br>" + foot_links if foot_links else ""}'
               f'<br>For internal use only.</div></div>')

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
  .r-inst {{ width:96px !important; }}
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
