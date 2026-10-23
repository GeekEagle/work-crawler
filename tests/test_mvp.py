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
