from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib import error, request

from .models import Contact, Draft


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "none"
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    send_resume_content: bool = False

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            provider=os.getenv("LLM_PROVIDER", "none").strip().lower(),
            base_url=os.getenv("LLM_BASE_URL", "").strip().rstrip("/"),
            api_key=os.getenv("LLM_API_KEY", "").strip(),
            model=os.getenv("LLM_MODEL", "").strip(),
            send_resume_content=os.getenv("LLM_SEND_RESUME_CONTENT", "false").strip().lower() == "true",
        )

    @property
    def enabled(self) -> bool:
        return self.provider not in {"", "none", "local"}


def _prompt_for(contact: Contact, resume_text: str = "") -> str:
    resume_section = resume_text if resume_text else "Resume content is unavailable; do not infer qualifications."
    return f"""You draft one concise, truthful recruiter email.

Rules:
- Use only the supplied contact, job, and resume facts.
- Never invent qualifications, employers, referrals, work authorization, availability, or prior conversations.
- Do not include sensitive personal data unless explicitly supplied for this draft.
- Return JSON with exactly two string fields: subject and body.

Contact/job facts:
- Contact: {contact.contact_name}
- Company: {contact.company}
- Contact title: {contact.job_title}
- Relevant role: {contact.relevant_job_title}
- Role tags: {contact.target_role_tags}
- Job URL: {contact.job_url}

Approved resume facts:
{resume_section}
"""


def _extract_json(content: str) -> dict[str, str]:
    value = content.strip()
    if value.startswith("```"):
        value = value.strip("`").removeprefix("json").strip()
    parsed = json.loads(value)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("subject"), str) or not isinstance(parsed.get("body"), str):
        raise ValueError("LLM response must contain string subject and body fields")
    return {"subject": parsed["subject"].strip(), "body": parsed["body"].strip()}


class LLMClient:
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig.from_env()

    def generate(self, contact: Contact, resume_text: str = "") -> dict[str, str]:
        if not self.config.enabled:
            raise RuntimeError("LLM provider is disabled")
        if not self.config.base_url or not self.config.api_key or not self.config.model:
            raise RuntimeError("LLM provider requires LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL")
        prompt = _prompt_for(contact, resume_text if self.config.send_resume_content else "")
        payload = json.dumps({
            "model": self.config.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": "You are a careful professional email drafting assistant."},
                {"role": "user", "content": prompt},
            ],
        }).encode("utf-8")
        endpoint = f"{self.config.base_url}/chat/completions"
        req = request.Request(endpoint, data=payload, method="POST", headers={
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        })
        try:
            with request.urlopen(req, timeout=45) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc
        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("LLM response did not contain chat completion content") from exc
        return _extract_json(content)


def create_llm_draft(contact: Contact, resume_path: str, client: LLMClient) -> Draft:
    result = client.generate(contact)
    return Draft(recipient=contact.email, subject=result["subject"], body=result["body"],
                 company=contact.company, source_url=contact.source_url,
                 resume_path=resume_path, approved=False, dry_run=True)
