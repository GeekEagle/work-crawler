from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv
from .job_sync import config_from_env, watch
from .linkedin import LinkedInConfig, authorization_url, exchange_code, get_userinfo
from .llm import LLMClient, LLMConfig
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
    draft_parser.add_argument("--llm", action="store_true", help="Use the configured LLM provider")

    linkedin_url_parser = subparsers.add_parser("linkedin-auth-url", help="Create LinkedIn OAuth authorization URL")
    linkedin_url_parser.add_argument("--config", default="llm-config.txt")

    linkedin_token_parser = subparsers.add_parser("linkedin-exchange", help="Exchange an OAuth code; never logs the token")
    linkedin_token_parser.add_argument("--code", required=True)
    linkedin_token_parser.add_argument("--config", default="llm-config.txt")

    linkedin_check_parser = subparsers.add_parser("linkedin-check-token", help="Check permitted LinkedIn identity access")
    linkedin_check_parser.add_argument("--token", required=True)

    sync_parser = subparsers.add_parser("sync-jobs", help="轮询公开职位来源并导出 Excel")
    sync_parser.add_argument("--source", choices=("adzuna", "jooble", "boards"), action="append")
    sync_parser.add_argument("--term", action="append", help="职位关键词，可多次指定")
    sync_parser.add_argument("--city", action="append", help="加拿大搜索地区，可多次指定")
    sync_parser.add_argument("--boards", default="", help="UTF-8 文件：平台|公司名称|公开 board slug")
    sync_parser.add_argument("--pages", type=int, default=1)
    sync_parser.add_argument("--interval", type=int, default=900, help="轮询间隔，秒；最小 300 秒")
    sync_parser.add_argument("--once", action="store_true", help="仅执行一次同步")
    sync_parser.add_argument("--database", default="data/jobs.sqlite3")
    sync_parser.add_argument("--output", default="output/latest_jobs.xlsx")
    send_parser = subparsers.add_parser("send")
    send_parser.add_argument("--drafts", required=True)
    send_parser.add_argument("--resume", required=True)
    send_parser.add_argument("--real-send", action="store_true", help="Reserved; real sending is not enabled in MVP")

    args = parser.parse_args()
    if args.command == "sync-jobs":
        load_dotenv()
        if args.pages < 1 or args.pages > 5:
            parser.error("--pages 需为 1–5")
        if not args.once and args.interval < 300:
            parser.error("--interval 至少 300 秒，以减少 API 请求")
        boards = Path(args.boards).read_text(encoding="utf-8-sig") if args.boards else ""
        config = config_from_env(args.source or [], args.term or [], args.city or [], args.pages, boards, args.interval)
        try:
            watch(config, args.database, args.output, once=args.once)
        except KeyboardInterrupt:
            print("已停止职位同步")
    elif args.command == "linkedin-auth-url":
        config = LinkedInConfig.from_env_or_file(config_path=args.config)
        url, state = authorization_url(config)
        print(f"Open this URL in your browser:\n{url}")
        print(f"Save this state value for callback verification (not a secret): {state}")
    elif args.command == "linkedin-exchange":
        config = LinkedInConfig.from_env_or_file(config_path=args.config)
        token_response = exchange_code(config, args.code)
        safe = {key: value for key, value in token_response.items() if key not in {"access_token", "refresh_token"}}
        print(json.dumps(safe, indent=2))
        print("Token exchange succeeded; store the token in a local secret manager, not Git.")
    elif args.command == "linkedin-check-token":
        profile = get_userinfo(args.token)
        safe = {key: profile.get(key) for key in ("sub", "name", "given_name", "family_name", "email", "email_verified") if key in profile}
        print(json.dumps(safe, indent=2))
    elif args.command == "export-workbook":
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
        llm_client = LLMClient(LLMConfig.from_env()) if args.llm else None
        drafts, blocked = build_drafts(contacts, args.resume, load_suppression(args.suppression), llm_client)
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




