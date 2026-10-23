from __future__ import annotations

import argparse
import json
from pathlib import Path

from .models import Contact
from .outreach import build_drafts, load_suppression
from .workbook import export_workbook, import_approved, read_contacts


def main() -> None:
    parser = argparse.ArgumentParser(description="Canada recruiter discovery and controlled outreach MVP")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export-workbook")
    export_parser.add_argument("--input", required=True)
    export_parser.add_argument("--output", required=True)

    import_parser = subparsers.add_parser("import-approved")
    import_parser.add_argument("--workbook", required=True)
    import_parser.add_argument("--output", required=True)

    draft_parser = subparsers.add_parser("draft-emails")
    draft_parser.add_argument("--approved", required=True)
    draft_parser.add_argument("--resume", required=True)
    draft_parser.add_argument("--output", required=True)
    draft_parser.add_argument("--suppression", default="data/suppression.csv")

    send_parser = subparsers.add_parser("send")
    send_parser.add_argument("--drafts", required=True)
    send_parser.add_argument("--resume", required=True)
    send_parser.add_argument("--real-send", action="store_true", help="Reserved; real sending is not enabled in MVP")

    args = parser.parse_args()
    if args.command == "export-workbook":
        contacts = read_contacts(args.input)
        path = export_workbook(contacts, args.output)
        print(f"Exported {len(contacts)} contacts to {path}")
    elif args.command == "import-approved":
        contacts, errors = import_approved(args.workbook)
        payload = {"contacts": [contact.to_dict() for contact in contacts], "errors": errors}
        Path(args.output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Approved {len(contacts)} contacts; validation errors: {len(errors)}")
        for error in errors:
            print(f"BLOCKED: {error}")
    elif args.command == "draft-emails":
        payload = json.loads(Path(args.approved).read_text(encoding="utf-8"))
        contacts = [Contact(**row) for row in payload["contacts"]]
        drafts, blocked = build_drafts(contacts, args.resume, load_suppression(args.suppression))
        Path(args.output).write_text(json.dumps({"drafts": [draft.to_dict() for draft in drafts], "blocked": blocked}, indent=2), encoding="utf-8")
        print(f"Generated {len(drafts)} drafts; blocked: {len(blocked)}")
    elif args.command == "send":
        payload = json.loads(Path(args.drafts).read_text(encoding="utf-8"))
        if args.real_send:
            raise SystemExit("Real sending is disabled in this MVP; configure and implement an approved OAuth provider adapter first.")
        print(f"DRY RUN: would preview {len(payload.get('drafts', []))} messages; no email was sent.")
        for draft in payload.get("drafts", []):
            print(f"TO: {draft['recipient']} | SUBJECT: {draft['subject']}")


if __name__ == "__main__":
    main()
