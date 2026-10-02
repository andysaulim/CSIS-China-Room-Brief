"""Web copy and archive for the brief.

Each issue is written as YYYY-MM-DD.html beside index.html (the latest) and
archive.html (every issue, newest first), with archive.json as the manifest.
Same shape as the China Daily Brief's public/ folder, so it can be served the
same way. The web copy must leave out anything not yet public: see the README.
"""

from __future__ import annotations

import json
from pathlib import Path

from .render import INK, MUTE, NAVY, RULE, SANS, SERIF, esc


def publish(site: Path, iso_date: str, html: str, entry: dict) -> None:
    site.mkdir(parents=True, exist_ok=True)
    (site / f"{iso_date}.html").write_text(html, encoding="utf-8")
    (site / "index.html").write_text(html, encoding="utf-8")
    manifest = site / "archive.json"
    rows = json.loads(manifest.read_text()) if manifest.exists() else []
    rows = [r for r in rows if r["date"] != iso_date] + [{"date": iso_date, **entry}]
    rows.sort(key=lambda r: r["date"], reverse=True)
    manifest.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    (site / "archive.html").write_text(archive_page(rows), encoding="utf-8")


def archive_page(rows: list[dict]) -> str:
    items = "".join(
        f'<tr><td style="padding:12px 16px 12px 0;vertical-align:top;white-space:nowrap;font-family:{SANS};'
        f'font-size:12px;color:{MUTE};border-bottom:1px solid {RULE};">{esc(r["date_line"])}</td>'
        f'<td style="padding:12px 0;vertical-align:top;border-bottom:1px solid {RULE};">'
        f'<a href="{esc(r["date"])}.html" style="font-family:{SERIF};font-size:16px;font-weight:700;color:{INK};">'
        f'{esc(r.get("label", "China Room Brief"))}</a>'
        f'<div style="font-family:{SERIF};font-size:14px;color:{MUTE};margin-top:3px;">{esc(r.get("re_line", ""))}</div>'
        f'</td></tr>' for r in rows)
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>China Room Brief: past issues</title>
<style>body{{margin:0;background:#EEF0F3;color:{INK}}} .w{{max-width:640px;margin:0 auto;background:#fff;padding:28px 32px 40px}}
@media (max-width:600px){{.w{{padding:20px 16px}} td{{display:block}} }}</style></head>
<body><div class="w">
<div style="font-family:{SANS};font-size:11px;"><strong style="letter-spacing:1.5px;">CSIS</strong>
<span style="color:{MUTE};"> &nbsp;Center for Strategic and International Studies</span></div>
<h1 style="margin:14px 0 12px;font-family:{SERIF};font-size:36px;line-height:1;">China Room Brief</h1>
<div style="height:2px;border-top:3px solid {NAVY};border-bottom:1px solid {NAVY};"></div>
<div style="font-family:{SANS};font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:{MUTE};margin:14px 0 6px;">Past issues</div>
<table width="100%" cellpadding="0" cellspacing="0" border="0">{items}</table>
<div style="font-family:{SANS};font-size:12px;margin-top:18px;"><a href="index.html" style="color:{INK};">Latest issue</a></div>
</div></body></html>"""
