"""Send an issue through Gmail SMTP, the same way the China Daily Brief does."""

from __future__ import annotations

import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def plain_text(html: str) -> str:
    t = re.sub(r"(?is)<(style|head).*?</\1>", "", html)
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d)>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"&nbsp;", " ", t).replace("&middot;", ",").replace("&amp;", "&")
    return re.sub(r"\n\s*\n+", "\n\n", t).strip()


def send(html: str, subject: str, to_env: str) -> list[str]:
    """to_env names the env var holding comma-separated recipients (DRAFT_TO or BRIEF_TO).
    Recipients go in BCC so the list is never exposed."""
    user, pw = os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASS"]
    sender = os.environ.get("GMAIL_FROM", user)
    rcpts = [r.strip() for r in os.environ[to_env].split(",") if r.strip()]
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, sender, sender
    msg.attach(MIMEText(plain_text(html), "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.sendmail(sender, rcpts, msg.as_string())
    return rcpts
