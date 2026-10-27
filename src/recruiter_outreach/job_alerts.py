"""Parse Indeed and LinkedIn job-alert emails and optionally read them via IMAP."""

from __future__ import annotations

import email
import imaplib
import os
import re
from email import policy
from email.message import Message
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urlparse


class _HTMLText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._href = ""
        self._anchor: list[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "a":
            self._href = attributes.get("href", "")
            self._anchor = []

    def handle_data(self, data):
        value = " ".join(data.split())
        if not value:
            return
        self.parts.append(value)
        if self._href:
            self._anchor.append(value)

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            self.links.append((self._href, " ".join(self._anchor).strip()))
            self._href = ""
            self._anchor = []


def _body(message: Message) -> str:
    if message.is_multipart():
        html = ""
        plain = ""
        for part in message.walk():
            if part.get_content_disposition() == "attachment":
                continue
            content = part.get_content()
            if part.get_content_type() == "text/html":
                html = content
            elif part.get_content_type() == "text/plain":
                plain = content
        return html or plain
    return message.get_content()


def _source(sender: str, subject: str, body: str) -> str:
    text = f"{sender} {subject} {body}".lower()
    if "linkedin" in text:
        return "LinkedIn Job Alert"
    if "indeed" in text:
        return "Indeed Job Alert"
    return "Email Job Alert"


def _is_job_link(url: str, source: str) -> bool:
    host = urlparse(url).netloc.lower()
    if "linkedin" in source.lower():
        return "linkedin.com" in host and ("/jobs/" in url or "/comm/jobs/" in url)
    if "indeed" in source.lower():
        return "indeed." in host and ("viewjob" in url or "/rc/" in url or "/pagead/" in url)
    return "linkedin.com/jobs/" in url or "indeed." in host


def _guess_location(text: str, anchor_index: int) -> str:
    lines = [line.strip(" -|·") for line in text.splitlines() if line.strip()]
    for line in lines[max(0, anchor_index - 2):anchor_index + 5]:
        if re.search(r"\b(canada|ontario|quebec|québec|alberta|british columbia|toronto|vancouver|montreal|ottawa|calgary|edmonton|waterloo|remote)\b", line, re.I):
            return line[:180]
    return "Canada" if re.search(r"\bcanada\b", text, re.I) else ""


def parse_alert(raw: bytes | str) -> list[dict]:
    message = email.message_from_bytes(raw, policy=policy.default) if isinstance(raw, bytes) else email.message_from_string(raw, policy=policy.default)
    sender = str(message.get("From", ""))
    subject = str(message.get("Subject", ""))
    body = _body(message)
    source = _source(sender, subject, body)
    parser = _HTMLText()
    parser.feed(body)
    text = "\n".join(parser.parts)
    jobs: list[dict] = []
    seen: set[str] = set()
    for url, anchor in parser.links:
        if not _is_job_link(url, source):
            continue
        title = anchor.strip()
        if len(title) < 3 or title.lower() in {"view job", "apply now", "see more jobs", "view all jobs"}:
            continue
        key = url.split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        position = text.find(title)
        nearby = text[max(0, position - 220):position + 500] if position >= 0 else text[:700]
        company = ""
        company_match = re.search(r"(?:at|@|company)\s*[:\-]?\s*([^\n|·]{2,100})", nearby, re.I)
        if company_match:
            company = company_match.group(1).strip()
        salary_match = re.search(r"(?:CA?\$|\$)\s?[\d,]+(?:\s*[-–]\s*(?:CA?\$|\$)?\s?[\d,]+)?(?:\s*(?:per year|/year|annually|an hour|/hr))?", nearby, re.I)
        jobs.append({
            "title": title,
            "company": company,
            "location": _guess_location(text, text[:position].count("\n") if position >= 0 else 0),
            "description": nearby,
            "url": url,
            "source": source,
            "posted": message.get("Date", ""),
            "salary": salary_match.group(0) if salary_match else "",
            "recruiter_email": "",
        })
    return jobs


def read_imap_alerts() -> tuple[list[dict], int]:
    host = os.getenv("ALERT_IMAP_HOST")
    user = os.getenv("ALERT_IMAP_USER")
    password = os.getenv("ALERT_IMAP_PASSWORD")
    folder = os.getenv("ALERT_IMAP_FOLDER", "INBOX")
    if not all((host, user, password)):
        raise ValueError("请配置 ALERT_IMAP_HOST、ALERT_IMAP_USER、ALERT_IMAP_PASSWORD；密码只存本机 .env")
    mailbox = imaplib.IMAP4_SSL(host, int(os.getenv("ALERT_IMAP_PORT", "993")))
    try:
        mailbox.login(user, password)
        mailbox.select(folder, readonly=True)
        status, data = mailbox.search(None, "OR FROM \"linkedin\" FROM \"indeed\"")
        if status != "OK":
            return [], 0
        messages: list[dict] = []
        for number in data[0].split():
            status, parts = mailbox.fetch(number, "(RFC822)")
            if status != "OK":
                continue
            raw = next((part[1] for part in parts if isinstance(part, tuple)), None)
            if raw:
                messages.extend(parse_alert(raw))
        return messages, len(data[0].split())
    finally:
        try:
            mailbox.logout()
        except Exception:
            pass
