import json
from pathlib import Path

from recruiter_outreach.models import Contact
from recruiter_outreach.outreach import build_drafts, validate_send_candidate
from recruiter_outreach.workbook import export_workbook, import_approved


def test_export_and_import_round_trip(tmp_path):
    workbook = tmp_path / "contacts.xlsx"
    export_workbook([Contact(contact_name="A", company="C", email="a@example.com", source_url="https://c.example")], workbook)
    contacts, errors = import_approved(workbook)
    assert contacts == []
    assert errors == []


def test_approved_row_imports(tmp_path):
    workbook = tmp_path / "contacts.xlsx"
    contact = Contact(contact_name="A", company="C", email="a@example.com", source_url="https://c.example", include="Y")
    export_workbook([contact], workbook)
    contacts, errors = import_approved(workbook)
    assert len(contacts) == 1
    assert not errors


def test_missing_source_is_blocked():
    contact = Contact(email="a@example.com")
    assert "missing_source_url" in validate_send_candidate(contact, set())


def test_suppression_blocks_draft():
    contact = Contact(email="a@example.com", source_url="https://source.example", permission_status="public-business-contact")
    drafts, blocked = build_drafts([contact], "resume.pdf", {"a@example.com"})
    assert drafts == []
    assert blocked[0]["reasons"] == ["suppressed_or_opted_out"]
import json

from recruiter_outreach.llm import LLMClient, LLMConfig
from recruiter_outreach.models import Contact


class FakeLLMClient(LLMClient):
    def generate(self, contact, resume_text=""):
        return {"subject": f"Role at {contact.company}", "body": "Hello, this is a grounded draft."}


def test_llm_draft_uses_structured_response():
    contact = Contact(email="a@example.com", company="Example", source_url="https://example.com", permission_status="public-business-contact")
    draft = __import__("recruiter_outreach.llm", fromlist=["create_llm_draft"]).create_llm_draft(contact, "resume.pdf", FakeLLMClient(LLMConfig(provider="test")))
    assert draft.subject == "Role at Example"
    assert draft.resume_path == "resume.pdf"


def test_disabled_llm_config_is_safe():
    config = LLMConfig(provider="none")
    assert not config.enabled
import urllib.parse

from recruiter_outreach.linkedin import LinkedInConfig, authorization_url


def test_authorization_url_contains_registered_callback_and_scopes():
    config = LinkedInConfig("client", "secret", "http://127.0.0.1:8000/callback")
    url, state = authorization_url(config, state="test-state")
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert query["client_id"] == ["client"]
    assert query["redirect_uri"] == [config.redirect_uri]
    assert query["scope"] == ["openid profile email"]
    assert query["state"] == ["test-state"]
    assert state == "test-state"
