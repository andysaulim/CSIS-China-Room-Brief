"""Send an issue through Gmail SMTP, the same way the China Daily Brief does.

The banner travels inside the email as an inline image (Content-ID), so it
shows without being hosted anywhere and keeps working if the repository is
private.
"""

from __future__ import annotations

import os
import re
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

BANNER_FILE = Path(__file__).resolve().parent.parent / "assets" / "banner_china_room.png"


def plain_text(html: str) -> str:
    t = re.sub(r"(?is)<(style|head).*?</\1>", "", html)
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d)>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"&nbsp;", " ", t).replace("&amp;", "&")
    return re.sub(r"\n\s*\n+", "\n\n", t).strip()


def send(html: str, subject: str, to_env: str, banner_src: str = "") -> list[str]:
    """to_env names the env var holding comma-separated recipients (DRAFT_TO or BRIEF_TO).
    Recipients go in BCC so the list is never exposed."""
    user, pw = os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASS"]
    sender = os.environ.get("GMAIL_FROM") or user
    rcpts = [r.strip() for r in os.environ[to_env].split(",") if r.strip()]

    inline = banner_src and BANNER_FILE.exists() and banner_src in html
    if inline:
        html = html.replace(banner_src, "cid:china-room-banner")
    root = MIMEMultipart("related")
    root["Subject"], root["From"], root["To"] = subject, sender, sender
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain_text(html), "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))
    root.attach(alt)
    if inline:
        img = MIMEImage(BANNER_FILE.read_bytes(), "png")
        img.add_header("Content-ID", "<china-room-banner>")
        img.add_header("Content-Disposition", "inline", filename="china-room-brief.png")
        root.attach(img)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.sendmail(sender, rcpts, root.as_string())
    return rcpts
