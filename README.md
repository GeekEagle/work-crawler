# Canada IT Recruiter Outreach Assistant

Safe MVP for discovering Canadian IT recruiter and job leads, reviewing them in Excel, generating personalized outreach, and sending only user-approved emails.

## MVP workflow

1. Configure target roles, locations, technologies, and work preferences.
2. Import user-provided contacts or collect permitted public business contacts and job leads.
3. Export an Excel workbook with provenance, confidence, source URLs, duplicate checks, and `Include` approval fields.
4. Manually review and filter the workbook; mark approved rows with `Include = Y`.
5. Re-import approved rows and generate deterministic drafts now; an LLM adapter can be added at the isolated drafting boundary.
6. Review messages, select the approved resume PDF, and run dry-run mode first.
7. Send only approved messages while enforcing limits, cooldowns, quiet hours, suppression/opt-out checks, and audit logging.

## Supported targeting

Roles include software developer/SDE, machine learning engineer, AI engineer, applied and generative AI engineer, LLM/RAG engineer, NLP, computer vision, deep learning, MLOps, ML platform, AI infrastructure, model serving/inference, data scientist/engineer, backend, frontend, full-stack, DevOps/cloud, QA automation, robotics, recommender systems, responsible AI, and related IT roles across Canada.

## Safe MVP boundaries

- Uses user-provided data, permitted public business contact pages, and officially authorized APIs or feeds.
- Does not request or store LinkedIn/Indeed passwords, scrape authenticated pages, bypass CAPTCHAs or rate limits, or guess private email addresses.
- Collects only professional contact data needed for outreach and preserves source URL, source type, timestamp, and confidence.
- Requires explicit user approval before every message or bounded batch; controlled auto-send is not enabled in this MVP.
- Never invents qualifications, employers, referrals, work authorization, availability, or prior conversations.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

## Commands

```powershell
python -m recruiter_outreach.cli export-workbook --input data\sample_contacts.csv --output output\recruiter_contacts.xlsx
python -m recruiter_outreach.cli import-approved --workbook output\recruiter_contacts.xlsx --output output\approved.json
python -m recruiter_outreach.cli draft-emails --approved output\approved.json --resume path\to\resume.pdf --output output\drafts.json
python -m recruiter_outreach.cli send --drafts output\drafts.json --resume path\to\resume.pdf
```

The last command is always a dry run in the MVP. Real delivery requires an approved OAuth email-provider adapter and explicit future implementation.

## Provider configuration

Copy `.env.example` to `.env` and fill in provider-specific values locally. Keep `.env`, resumes, exports, tokens, and logs out of source control. Use OAuth or provider tokens; never put credentials in source code.

## Data handling

The Excel export is the primary review surface. It includes recruiter contacts, provenance, approval/status fields, and a README sheet; optional job-lead support is planned in the same workbook format. Provide deletion and export controls for user data. Obtain applicable legal/compliance review before production outreach in Canada.
