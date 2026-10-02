"""CSIS China Room Brief: issue dict -> table-based HTML email, in one of
three designs.

  newsroom   Axios AM / POLITICO Playbook: one sans family, big type, a short
             colored rule over each section title, numbered stories, no bars.
  pubs       CSIS publications: Libre Baskerville over Source Sans 3 on a
             parchment ground, blue kicker over a serif title, hairlines.
  briefing   Semafor / Bloomberg newsletters: each section a white card on a
             grey ground under a navy header that carries a count.

All three share the CSIS comms top (internal-use strip, the 600 x 200 CSIS
banner), the By the numbers strip, and the navy contact band at the foot.
Web fonts load where the client allows (Apple Mail, iOS, Outlook for Mac);
Gmail and Outlook for Windows fall back to Georgia and Arial.

Two modes. "draft" is the Thursday-noon copy for review: human-owned sections
show their brief and the agent's candidates. "final" is what goes out Friday:
an empty section is left out, never padded.
"""

from __future__ import annotations

import re
from datetime import date as _date

# Shared CSIS colors
BANNER_NAVY = "#001F59"   # sampled from the CSIS comms banner
CERULEAN = "#007DAD"      # the banner's label-box outline
NAVY = "#004165"          # CSIS navy
NAVY_BRIGHT = "#0065A6"
INK = "#1A1A1A"
MUTE = "#6B625A"
RULE = "#E3DCCF"
SERIF = "Georgia,'Times New Roman',serif"
SANS = "Arial,Helvetica,sans-serif"
SLOT_BG = "#F7F8FA"

FONT_LINK = ('<link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700'
             '&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">')
LB = "'Libre Baskerville',Georgia,'Times New Roman',serif"
SS = "'Source Sans 3','Segoe UI',Arial,Helvetica,sans-serif"

THEMES = {
    "newsroom": {
        "page": "#EEF0F3", "body_bg": "#FFFFFF", "head": SS, "text": SS, "label": SS,
        "ink": "#111418", "body": "#2A2E35", "mute": "#5F6670", "rule": "#E3E6EA",
        "accent": CERULEAN, "navy": BANNER_NAVY, "size": 16, "hl": 19, "news_hl": 22,
    },
    "pubs": {
        "page": "#E9E4D8", "body_bg": "#F5F2EB", "head": LB, "text": SS, "label": SS,
        "ink": "#1A1A1A", "body": "#2E2B28", "mute": "#6B625A", "rule": "#D4CFC8",
        "accent": NAVY_BRIGHT, "navy": NAVY, "size": 16, "hl": 17, "news_hl": 19,
    },
    "briefing": {
        "page": "#E6E9EE", "body_bg": "#E6E9EE", "head": SS, "text": SS, "label": SS,
        "ink": "#111418", "body": "#2A2E35", "mute": "#5F6670", "rule": "#E3E6EA",
        "accent": CERULEAN, "navy": BANNER_NAVY, "size": 16, "hl": 18, "news_hl": 20,
    },
}

SECTIONS = [
    ("week_at_a_glance", "Week at a Glance", "ahead"),
    ("heard_on_the_hill", "Heard on the Hill", "back"),
    ("in_the_news", "In the News", "back"),
    ("research_roundup", "Research Roundup", "back"),
    ("in_the_works", "In the Works @ CSIS", "ahead"),
    ("on_the_horizon", "On the Horizon", "ahead"),
]
KICKER = {
    "week_at_a_glance": "Next week", "heard_on_the_hill": "Congress", "in_the_news": "Top five",
    "research_roundup": "Think tanks and CRS", "in_the_works": "CSIS scholars", "on_the_horizon": "Calendar",
}


def esc(text) -> str:
    if text is None:
        return ""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _full(iso: str) -> str:
    d = _date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}"


class R:
    """Renderer bound to one theme."""

    def __init__(self, theme: str):
        self.name = theme
        self.t = THEMES[theme]

    # ---- primitives ----
    def link(self, text, url):
        if not url:
            return text
        return f'<a href="{esc(url)}" style="color:{self.t["ink"]};text-decoration:none;">{text}</a>'

    def tag(self, text):
        t = self.t
        if not text:
            return ""
        color = t["accent"] if self.name != "pubs" else t["mute"]
        return (f'<div style="font-family:{t["label"]};font-size:13px;font-weight:700;color:{color};'
                f'margin-bottom:3px;">{text}</div>')

    def body(self, text, top=5):
        t = self.t
        if not text:
            return ""
        return (f'<div style="font-family:{t["text"]};font-size:{t["size"]}px;line-height:1.55;color:{t["body"]};'
                f'margin-top:{top}px;">{esc(text)}</div>')

    def headline(self, text, url, size=None):
        t = self.t
        return (f'<div style="font-family:{t["head"]};font-size:{size or t["hl"]}px;font-weight:700;'
                f'line-height:1.3;color:{t["ink"]};">{self.link(esc(text), url)}</div>')

    def axiom(self, label, text):
        t = self.t
        return (f'<div style="font-family:{t["text"]};font-size:{t["size"]}px;line-height:1.55;color:{t["body"]};'
                f'margin-top:6px;"><strong style="color:{t["ink"]};">{esc(label)}:</strong> {esc(text)}</div>')

    def bullets(self, points):
        t = self.t
        if not points:
            return ""
        lis = "".join(f'<li style="margin:0 0 4px;">{esc(p)}</li>' for p in points)
        return (f'<ul style="margin:6px 0 0 18px;padding:0;font-family:{t["text"]};font-size:{t["size"]}px;'
                f'line-height:1.5;color:{t["body"]};">{lis}</ul>')

    def sep(self, first):
        return "" if first else f"border-top:1px solid {self.t['rule']};"

    # ---- section frame ----
    def section(self, key, title, inner, count=""):
        t = self.t
        anchor = f'<a name="{key}" id="{key}"></a>'
        if self.name == "newsroom":
            return (f'<div class="sec" style="padding:30px 32px 8px;">{anchor}'
                    f'<div style="width:44px;height:4px;background:{t["accent"]};margin-bottom:10px;"></div>'
                    f'<div style="font-family:{t["head"]};font-size:26px;font-weight:700;color:{t["ink"]};'
                    f'letter-spacing:-0.3px;margin-bottom:6px;">{esc(title)}</div>{inner}</div>')
        if self.name == "pubs":
            return (f'<div class="sec" style="padding:30px 32px 8px;">{anchor}'
                    f'<div style="font-family:{t["label"]};font-size:12px;font-weight:700;letter-spacing:1.5px;'
                    f'text-transform:uppercase;color:{t["accent"]};">{esc(KICKER.get(key, ""))}</div>'
                    f'<div style="font-family:{t["head"]};font-size:24px;font-weight:400;color:{t["ink"]};'
                    f'margin:4px 0 8px;padding-bottom:10px;border-bottom:1px solid {t["ink"]};">{esc(title)}</div>'
                    f'{inner}</div>')
        # briefing: white card with a navy header carrying a count
        cnt = (f'<td align="right" style="font-family:{t["label"]};font-size:12px;color:#B9C6DA;white-space:nowrap;">'
               f'{esc(count)}</td>') if count else ""
        return (f'<div class="sec" style="padding:0 20px 16px;">{anchor}'
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#FFFFFF;">'
                f'<tr><td style="background:{t["navy"]};padding:13px 24px;">'
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
                f'<td style="font-family:{t["head"]};font-size:17px;font-weight:700;color:#FFFFFF;">{esc(title)}</td>'
                f'{cnt}</tr></table></td></tr>'
                f'<tr><td class="card-in" style="padding:8px 24px 14px;">{inner}</td></tr></table></div>')

    def part(self, label, dek):
        t = self.t
        if self.name == "briefing":
            return (f'<div class="sec" style="padding:14px 20px 10px;font-family:{t["label"]};font-size:13px;'
                    f'font-weight:700;letter-spacing:1px;text-transform:uppercase;color:{t["navy"]};">'
                    f'{esc(label)} <span style="font-weight:400;letter-spacing:0;text-transform:none;color:{t["mute"]};">'
                    f'&nbsp;{esc(dek)}</span></div>')
        color = t["accent"] if self.name == "newsroom" else t["navy"]
        return (f'<div class="sec" style="padding:40px 32px 0;">'
                f'<div style="font-family:{t["head"]};font-size:15px;font-weight:700;letter-spacing:1.5px;'
                f'text-transform:uppercase;color:{color};">{esc(label)}'
                f'<span style="font-family:{t["label"]};font-weight:400;letter-spacing:0;text-transform:none;'
                f'color:{t["mute"]};"> &nbsp;{esc(dek)}</span></div></div>')

    # ---- content blocks ----
    def items(self, items):
        out = []
        for n, i in enumerate(items):
            why = self.axiom("Why it matters", i["why"]) if i.get("why") else ""
            out.append(f'<div style="padding:16px 0 18px;{self.sep(n == 0)}">{self.tag(i.get("tag", ""))}'
                       f'{self.headline(i["headline"], i.get("url", ""))}{self.body(i.get("body", ""))}'
                       f'{why}{self.bullets(i.get("bullets", []))}</div>')
        return "".join(out)

    def news(self, items):
        t = self.t
        out = []
        for n, i in enumerate(items, 1):
            why = self.axiom("Why it matters", i["why"]) if i.get("why") else ""
            num_color = t["accent"] if self.name != "pubs" else t["navy"]
            out.append(
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="{self.sep(n == 1)}"><tr>'
                f'<td width="46" style="padding:16px 0;vertical-align:top;font-family:{t["head"]};font-size:34px;'
                f'font-weight:700;line-height:1;color:{num_color};">{n}</td>'
                f'<td style="padding:16px 0 18px;vertical-align:top;">{self.tag(i.get("tag", ""))}'
                f'{self.headline(i["headline"], i.get("url", ""), t["news_hl"])}{self.body(i.get("body", ""), 7)}{why}'
                f'</td></tr></table>')
        return "".join(out)

    def research(self, items):
        t = self.t
        out = []
        for n, i in enumerate(items):
            out.append(
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="{self.sep(n == 0)}"><tr>'
                f'<td width="130" class="r-inst" style="padding:14px 14px 14px 0;vertical-align:top;">'
                f'<div style="font-family:{t["label"]};font-size:14px;font-weight:700;line-height:1.3;color:{t["navy"]};">'
                f'{esc(i["institution"])}</div>'
                f'<div style="font-family:{t["label"]};font-size:12px;color:{t["mute"]};margin-top:3px;">{esc(i.get("date", ""))}</div></td>'
                f'<td class="r-main" style="padding:14px 0;vertical-align:top;">{self.headline(i["headline"], i.get("url", ""))}'
                f'{self.body(i.get("body", ""))}</td></tr></table>')
        return "".join(out)

    def agenda(self, items):
        t = self.t
        html, current, first = "", None, True
        for i in items:
            g = i.get("group", "")
            if g != current:
                current, first = g, True
                html += (f'<div style="font-family:{t["label"]};font-size:13px;font-weight:700;color:{t["navy"]};'
                         f'margin:{"6px" if not html else "20px"} 0 0;padding-bottom:6px;'
                         f'border-bottom:2px solid {t["navy"]};">{esc(g)}</div>')
            day = i.get("day") or ""
            meta = (f'<div style="font-family:{t["label"]};font-size:13px;color:{t["mute"]};margin-top:2px;">'
                    f'{esc(i.get("kind", ""))}</div>') if i.get("kind") else ""
            day_td = (f'<td width="64" style="padding:12px 10px 12px 0;vertical-align:top;font-family:{t["head"]};'
                      f'font-size:20px;font-weight:700;line-height:1.1;color:{t["navy"]};white-space:nowrap;">{esc(day)}</td>'
                      ) if day else ""
            html += (f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
                     f'style="border-bottom:1px solid {t["rule"]};"><tr>{day_td}'
                     f'<td style="padding:12px 0;vertical-align:top;">{self.headline(i["headline"], i.get("url", ""), t["hl"] - 1)}'
                     f'{meta}{self.body(i.get("detail", ""), 3)}</td></tr></table>')
            first = False
        cut = html.rfind(f'style="border-bottom:1px solid {t["rule"]};"')
        if cut >= 0:
            html = html[:cut] + 'style=""' + html[cut + len(f'style="border-bottom:1px solid {t["rule"]};"'):]
        return html

    def horizon(self, s):
        """Next 30 days in full; later dates one line each."""
        t = self.t
        def type_label(e):
            color = "#B52B2B" if e["type"] == "Deadline" else t["accent"]
            return (f'<span style="font-family:{t["label"]};font-size:12px;font-weight:700;letter-spacing:0.5px;'
                    f'text-transform:uppercase;color:{color};">{esc(e["type"])}</span>')
        def head(x, top):
            return (f'<div style="font-family:{t["label"]};font-size:13px;font-weight:700;color:{t["navy"]};'
                    f'margin:{top} 0 0;padding-bottom:6px;border-bottom:2px solid {t["navy"]};">{x}</div>')
        html = ""
        if s.get("near"):
            html += head("Next 30 days", "6px")
            for n, e in enumerate(s["near"]):
                mon = e["group"].split(" ")[0][:3].upper()
                where = (f'<div style="font-family:{t["label"]};font-size:13px;color:{t["mute"]};margin-top:3px;">'
                         f'{esc(e["where"])}</div>') if e.get("where") else ""
                html += (f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
                         f'style="{"" if n == len(s["near"]) - 1 else "border-bottom:1px solid " + t["rule"] + ";"}"><tr>'
                         f'<td width="70" style="padding:14px 10px 14px 0;vertical-align:top;">'
                         f'<div style="font-family:{t["label"]};font-size:12px;font-weight:700;letter-spacing:1px;color:{t["mute"]};">{mon}</div>'
                         f'<div style="font-family:{t["head"]};font-size:22px;font-weight:700;line-height:1.1;color:{t["navy"]};'
                         f'white-space:nowrap;">{esc(e["day"])}</div></td>'
                         f'<td style="padding:14px 0;vertical-align:top;">{type_label(e)}'
                         f'<div style="margin-top:2px;">{self.headline(e["headline"], e.get("url", ""))}</div>'
                         f'{self.body(e.get("angle", ""), 4)}{where}</td></tr></table>')
        if s.get("far"):
            html += head("Further out", "22px")
            for n, e in enumerate(s["far"]):
                when = e["group"].split(" ")[0] + (f' {e["day"]}' if e["day"] and e["day"] != "TBC" else " (TBC)")
                where = f', {esc(e["where"])}' if e.get("where") else ""
                html += (f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
                         f'style="{"" if n == len(s["far"]) - 1 else "border-bottom:1px solid " + t["rule"] + ";"}"><tr>'
                         f'<td width="120" style="padding:10px 10px 10px 0;vertical-align:top;font-family:{t["label"]};'
                         f'font-size:14px;font-weight:700;color:{t["navy"]};">{esc(when)}</td>'
                         f'<td style="padding:10px 0;vertical-align:top;">'
                         f'<div style="font-family:{t["text"]};font-size:15px;font-weight:700;color:{t["ink"]};">'
                         f'{self.link(esc(e["headline"]), e.get("url", ""))}</div>'
                         f'<div style="font-family:{t["label"]};font-size:13px;color:{t["mute"]};margin-top:2px;">'
                         f'<span style="font-weight:700;color:{"#B52B2B" if e["type"] == "Deadline" else t["accent"]};">'
                         f'{esc(e["type"])}</span>{where}</div>'
                         f'{self.body(e.get("angle", ""), 3) if e.get("angle") else ""}'
                         f'</td></tr></table>')
        return html

    def docket(self, dk, issue_iso):
        t = self.t
        if not dk or not (dk.get("hearings") or dk.get("bills")):
            return ""
        def head(x):
            return (f'<div style="font-family:{t["label"]};font-size:13px;font-weight:700;color:{t["navy"]};'
                    f'margin:18px 0 0;padding-bottom:6px;border-bottom:2px solid {t["navy"]};">{x}</div>')
        def row(left, title, url, meta):
            return (f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:1px solid {t["rule"]};"><tr>'
                    f'<td width="110" style="padding:10px 12px 10px 0;vertical-align:top;font-family:{t["label"]};font-size:13px;'
                    f'font-weight:700;color:{t["navy"]};">{left}</td>'
                    f'<td style="padding:10px 0;vertical-align:top;">{self.headline(title, url, t["hl"] - 2)}'
                    f'<div style="font-family:{t["label"]};font-size:13px;color:{t["mute"]};margin-top:2px;">{meta}</div></td></tr></table>')
        html = ""
        if dk.get("hearings"):
            html += head("Hearings")
            for h in dk["hearings"]:
                when = _full(h["date"]) + (f"<br><span style='font-weight:400;color:{t['mute']};'>scheduled</span>"
                                           if h["date"] >= issue_iso else "")
                html += row(when, h["title"], h.get("url", ""), esc(f'{h["chamber"]}: {h["committee"]}'))
        if dk.get("bills"):
            html += head("New legislation")
            for b in dk["bills"]:
                html += row(esc(b["number"]), b["title"], b.get("url", ""),
                            esc(f'{b["sponsor"]}, introduced {_full(b["introduced"])}'))
        return html

    def numbers(self, nums):
        """By the numbers: four figures from the week's sources."""
        t = self.t
        if not nums:
            return ""
        cells = ""
        for n, x in enumerate(nums[:4]):
            edge = f"border-left:1px solid {t['rule']};" if n else ""
            src = (f'<div style="font-family:{t["label"]};font-size:11px;color:{t["mute"]};margin-top:4px;">'
                   f'{esc(x.get("source", ""))}</div>') if x.get("source") else ""
            fig = f'<a href="{esc(x["url"])}" style="color:inherit;text-decoration:none;">{esc(x["figure"])}</a>' if x.get("url") else esc(x["figure"])
            cells += (f'<td class="num-cell" width="25%" style="padding:4px 12px;vertical-align:top;{edge}">'
                      f'<div style="font-family:{t["head"]};font-size:{19 if self.name == "pubs" else 21}px;font-weight:700;line-height:1.15;white-space:nowrap;'
                      f'color:{t["navy"]};">{fig}</div>'
                      f'<div style="font-family:{t["label"]};font-size:13px;line-height:1.35;color:{t["body"]};margin-top:4px;">'
                      f'{esc(x["label"])}</div>{src}</td>')
        bg = "#FFFFFF" if self.name == "briefing" else ("#EEEAE0" if self.name == "pubs" else "#F3F6F9")
        pad = "0 20px 16px" if self.name == "briefing" else "4px 32px 8px"
        return (f'<div class="sec" style="padding:{pad};">'
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{bg};">'
                f'<tr><td style="padding:14px 8px 4px 20px;font-family:{t["label"]};font-size:12px;font-weight:700;'
                f'letter-spacing:1px;text-transform:uppercase;color:{t["accent"] if self.name != "pubs" else t["navy"]};">'
                f'By the numbers</td></tr>'
                f'<tr><td style="padding:6px 8px 16px;"><table width="100%" cellpadding="0" cellspacing="0" border="0" style="table-layout:fixed;">'
                f'<tr class="num-row">{cells}</tr></table></td></tr></table></div>')


def slot(spec, candidates=None, note=""):
    rows = ""
    for c in candidates or []:
        meta = ", ".join(esc(x) for x in (c.get("date_label"), c.get("source")) if x)
        url = c.get("url", "")
        txt = f'<a href="{esc(url)}" style="color:#1A1A1A;">{esc(c["text"])}</a>' if url else esc(c["text"])
        rows += f'<li style="margin:0 0 6px;">{txt}<span style="color:#6B625A;font-size:12px;"> &nbsp;{meta}</span></li>'
    lst = (f'<ul style="margin:8px 0 0 18px;padding:0;font-family:{SANS};font-size:13px;line-height:1.45;'
           f'color:#2E2B28;">{rows}</ul>') if rows else ""
    note_html = f'<div style="font-family:{SANS};font-size:13px;color:#2E2B28;margin-top:6px;">{note}</div>' if note else ""
    return (f'<div style="background:{SLOT_BG};border:1px dashed #B8B0A3;padding:12px 14px;margin-top:8px;">'
            f'<div style="font-family:{SANS};font-size:12px;font-weight:700;color:{NAVY};">For the coordinator</div>'
            f'<div style="font-family:{SANS};font-size:12px;color:#1A1A1A;margin-top:4px;">{esc(spec)}</div>'
            f'{note_html}{lst}</div>')


def word_count(issue: dict) -> int:
    parts = [issue.get("editors_note", "")]
    for key, *_ in SECTIONS:
        for it in issue.get(key, {}).get("items", []):
            parts += [it.get("headline", ""), it.get("body", ""), it.get("detail", ""), it.get("why", "")]
            parts += it.get("bullets", [])
    return len(re.findall(r"[\w'’$%.,-]+", " ".join(parts)))


COUNT = {"in_the_news": "{n} stories", "research_roundup": "{n} reports", "heard_on_the_hill": "{n} items",
         "week_at_a_glance": "{n} to watch", "in_the_works": "{n} coming", "on_the_horizon": "{n} dates"}


def render(issue: dict, mode: str = "final", theme: str = "briefing") -> str:
    r = R(theme)
    t = r.t
    draft = mode == "draft"
    mins = max(1, round(word_count(issue) / 230))
    web_url, archive_url = issue.get("web_url", ""), issue.get("archive_url", "")
    out = []

    flag = "For internal use only"
    if draft:
        flag += f' &nbsp;&nbsp; <span style="color:#B52B2B;">Draft for review: {esc(issue.get("draft_for", ""))}</span>'
    ul = f'color:#3D4149;font-family:{SANS};font-size:11px;font-weight:700;text-decoration:underline;margin:0 0 0 14px;'
    links = "".join(f'<a href="{esc(u)}" style="{ul}">{lbl}</a>'
                    for lbl, u in (("Read online", web_url), ("Past issues", archive_url)) if u)
    out.append(f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#E7E7E7;" class="util-row">'
               f'<tr><td class="util-cell" style="padding:9px 20px;font-family:{SANS};font-size:11px;font-weight:700;'
               f'color:#3D4149;">{flag}</td><td class="util-cell" align="right" style="padding:9px 20px;white-space:nowrap;">'
               f'{links}</td></tr></table>')
    if issue.get("banner_src"):
        out.append(f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
                   f'<td align="center" bgcolor="{BANNER_NAVY}" style="background:{BANNER_NAVY};line-height:0;">'
                   f'<img src="{esc(issue["banner_src"])}" width="600" height="200" alt="CSIS China Room Brief" '
                   f'style="display:block;margin:0 auto;width:100%;max-width:600px;height:auto;border:0;color:#FFFFFF;'
                   f'font-family:{SERIF};font-size:28px;font-weight:700;line-height:1.2;"></td></tr></table>')

    # Masthead block: date, reading time, editor's note, contents
    note = (f'<div style="font-family:{t["text"]};font-size:{t["size"]}px;line-height:1.55;color:{t["body"]};margin-top:8px;">'
            f'{esc(issue["editors_note"])}</div>') if issue.get("editors_note") else ""
    present = [(k, ti) for k, ti, _ in SECTIONS if draft or issue.get(k, {}).get("items")]
    toc = "".join(
        f'<tr><td width="50%" style="padding:3px 0;">{a}</td><td width="50%" style="padding:3px 0;">{b}</td></tr>'
        for a, b in zip(*[iter([f'<a href="#{k}" style="font-family:{t["label"]};font-size:14px;font-weight:700;'
                                f'color:{t["navy"]};text-decoration:none;">{esc(ti)}</a>' for k, ti in present]
                               + ([""] if len(present) % 2 else []))] * 2))
    mast = (f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
            f'<td class="mast-main" style="font-family:{t["head"]};font-size:20px;font-weight:700;color:{t["ink"]};">'
            f'{esc(issue["date_line"])}</td>'
            f'<td class="mast-meta" align="right" style="font-family:{t["label"]};font-size:13px;color:{t["mute"]};'
            f'white-space:nowrap;">{mins} min read</td></tr></table>{note}'
            f'<div style="margin-top:14px;padding-top:12px;border-top:1px solid {t["rule"]};">'
            f'<table width="100%" cellpadding="0" cellspacing="0" border="0">{toc}</table></div>')
    if theme == "briefing":
        out.append(f'<div class="sec" style="padding:16px 20px;"><div class="card-in" style="background:#FFFFFF;'
                   f'padding:20px 24px 18px;">{mast}</div></div>')
    else:
        out.append(f'<div class="sec" style="padding:22px 32px 18px;">{mast}</div>')
    out.append(r.numbers(issue.get("by_the_numbers") or []))

    def sec(key):
        _, title, half = next(x for x in SECTIONS if x[0] == key)
        s = issue.get(key, {})
        items = s.get("items", [])
        if key == "on_the_horizon" and ("near" in s or "far" in s):
            inner = r.horizon(s)
        elif key in ("in_the_works", "on_the_horizon"):
            inner = r.agenda(items)
        elif key == "in_the_news":
            inner = r.news(items)
        elif key == "research_roundup" and items and "institution" in items[0]:
            inner = r.research(items)
        else:
            inner = r.items(items)
            if key == "heard_on_the_hill":
                inner += r.docket(s.get("docket") or {}, issue.get("iso", "9999"))
        if draft and (not inner or s.get("candidates") or s.get("gap")):
            inner += slot(s.get("spec", ""), s.get("candidates"), s.get("gap", ""))
        if inner:
            out.append(r.section(key, title, inner, COUNT.get(key, "").format(n=len(items)) if items else ""))

    sec("week_at_a_glance")
    out.append(r.part("The Week That Was", issue.get("back_window", "")))
    for k in ("heard_on_the_hill", "in_the_news", "research_roundup"):
        sec(k)
    out.append(r.part("The Week Ahead", issue.get("ahead_window", "")))
    for k in ("in_the_works", "on_the_horizon"):
        sec(k)

    c = issue.get("contact") or {}
    contact = ""
    if c.get("email"):
        title = f', {esc(c["title"])},' if c.get("title") else ""
        contact = (f'<div style="font-family:{t["head"]};font-size:17px;font-weight:700;color:#FFFFFF;">Questions?</div>'
                   f'<div style="font-family:{t["text"]};font-size:15px;line-height:1.6;color:#DCE4EC;margin-top:4px;">'
                   f'Reach out to {esc(c.get("name", ""))}{title} at '
                   f'<a href="mailto:{esc(c["email"])}" style="color:#FFFFFF;">{esc(c["email"])}</a>.</div>')
    out.append(f'<div class="sec bottom-band" style="background:{BANNER_NAVY};padding:26px 32px 28px;margin-top:24px;">{contact}'
               f'<div style="font-family:{t["label"]};font-size:13px;color:#9FB2C8;margin-top:16px;padding-top:14px;'
               f'border-top:1px solid #2E4677;">The China Room Brief is compiled by CSIS External Relations.</div></div>')

    body = "\n".join(out)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light">
{FONT_LINK}
<title>China Room Brief, {esc(issue["date_line"])}</title>
<style>
body {{ margin:0; padding:0; background:{t["page"]}; -webkit-text-size-adjust:100%; }}
.container {{ width:680px; max-width:100%; margin:0 auto; background:{t["body_bg"]}; }}
@media only screen and (max-width:680px) {{
  .sec {{ padding-left:16px !important; padding-right:16px !important; }}
  .card-in {{ padding-left:14px !important; padding-right:14px !important; }}
  .util-row .util-cell {{ display:block !important; text-align:left !important; padding:6px 16px !important; }}
  .util-row a {{ margin:0 14px 0 0 !important; }}
  .mast-main, .mast-meta {{ display:block !important; width:100% !important; text-align:left !important; }}
  .r-inst, .r-main {{ display:block !important; width:100% !important; }}
  .r-inst {{ padding:14px 0 4px !important; }}
  .r-main {{ padding:0 0 14px !important; }}
  .num-row .num-cell {{ display:inline-block !important; width:46% !important; border-left:0 !important;
                        padding:8px 2% !important; vertical-align:top !important; }}
}}
</style></head>
<body><div class="container">
{body}
</div></body></html>"""
