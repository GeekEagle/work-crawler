from __future__ import annotations

import re
from pathlib import Path

from .llm import LLMClient, create_llm_draft
from .models import Contact, Draft


def load_suppression(path: str | Path | None) -> set[str]:
    if not path or not Path(path).exists():
        return set()
    values = set()
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        value = line.strip().casefold()
        if value and not value.startswith("email"):
            values.add(value)
    return values


def validate_send_candidate(contact: Contact, suppression: set[str]) -> list[str]:
    errors: list[str] = []
    email = contact.email.strip().casefold()
    if not email or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        errors.append("invalid_email")
    if email in suppression or contact.opt_out.strip().upper() == "Y":
        errors.append("suppressed_or_opted_out")
    if not contact.source_url:
        errors.append("missing_source_url")
    if contact.permission_status.strip().casefold() in {"blocked", "opted-out"}:
        errors.append("permission_blocked")
    if contact.status.strip().casefold() == "do_not_contact":
        errors.append("do_not_contact")
    return errors


def create_draft(contact: Contact, resume_path: str | Path) -> Draft:
    name = contact.contact_name or "Hiring Team"
    role = contact.relevant_job_title or contact.job_title or "an IT opportunity"
    company = contact.company or "your organization"
    subject = f"Interest in {role} opportunities at {company}"
    body = (f"Hello {name},\n\n"
            f"I am exploring {role} opportunities in Canada and noticed {company} is connected to this area. "
            "My background and current interests are summarized in the attached resume. "
            "If my experience may fit a current or upcoming opportunity, I would appreciate the chance to speak.\n\n"
            "Thank you for your time,\n"
            "[Your Name]\n")
    return Draft(recipient=contact.email, subject=subject, body=body,
                 company=company, source_url=contact.source_url,
                 resume_path=str(resume_path), approved=False, dry_run=True)


def build_drafts(contacts: list[Contact], resume_path: str | Path, suppression: set[str], llm_client: LLMClient | None = None) -> tuple[list[Draft], list[dict]]:
    drafts: list[Draft] = []
    blocked: list[dict] = []
    for contact in contacts:
        reasons = validate_send_candidate(contact, suppression)
        if reasons:
            blocked.append({"email": contact.email, "reasons": reasons})
            continue
        if llm_client is not None:
            try:
                drafts.append(create_llm_draft(contact, str(resume_path), llm_client))
                continue
            except RuntimeError as exc:
                blocked.append({"email": contact.email, "reasons": ["llm_error", str(exc)]})
                continue
        drafts.append(create_draft(contact, resume_path))
    return drafts, blocked
