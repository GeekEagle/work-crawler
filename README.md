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

The Excel export is the primary review surface. It includes recruiter contacts, provenance, approval/status fields, and a README sheet; Job lead synchronization is now available through the `sync-jobs` CLI; the workbook is the primary review surface. Provide deletion and export controls for user data. Obtain applicable legal/compliance review before production outreach in Canada.


## LinkedIn OAuth diagnostics

The project now includes an OAuth helper for permitted LinkedIn identity access. It does not scrape LinkedIn or provide recruiter/job-directory access.

1. In the LinkedIn Developer Portal, register an exact redirect URI such as `http://127.0.0.1:8000/auth/linkedin/callback` if supported by your app configuration.
2. Add the redirect URI to `llm-config.txt` as `LinkedIn Redirect URI=...`, or set `LINKEDIN_REDIRECT_URI` in the local environment.
3. Configure the scopes approved by LinkedIn. The default is `openid profile email`.
4. Generate an authorization URL:

```powershell
$env:LINKEDIN_REDIRECT_URI='http://127.0.0.1:8000/auth/linkedin/callback'
python -m recruiter_outreach.cli linkedin-auth-url
```

5. Open the printed URL in a browser and authorize the application.
6. Use the returned callback `code` with `linkedin-exchange`. The CLI never prints the access token.
7. Check basic permitted identity access with `linkedin-check-token` using the token locally.

The current implementation only tests the official identity endpoint. Job or recruiter data requires a separately approved LinkedIn product and scope; no unsupported endpoint is called.

## 定时发现加拿大最新职位

`work-assistant` 已有的 Adzuna、Jooble、Ashby、Lever、Greenhouse 来源、SQLite 指纹去重和 `first_seen`/`last_seen` 已并入 `src/recruiter_outreach/`。主项目保留联系人 Excel、LLM 草稿和 LinkedIn OAuth 诊断，现阶段**不启用**原项目的 SMTP 自动发送。这里的“实时”指按间隔轮询公开来源，不是推送或保证全网零延迟。

配置合法来源：

- Adzuna：在本地 `.env` 中填 `ADZUNA_APP_ID` 和 `ADZUNA_APP_KEY`。
- Jooble：在本地 `.env` 中填 `JOOBLE_API_KEY`。
- 企业招聘板：先从企业官网核实确实使用 Ashby、Lever 或 Greenhouse，再把 `平台|公司|slug` 按行写入本地 UTF-8 文件，例如 `data/boards.txt`。

只抓一次：

```powershell
python -m recruiter_outreach.cli sync-jobs --source boards --boards data/boards.txt --once
```

持续轮询（默认每 900 秒；按 `Ctrl+C` 停止）：

```powershell
python -m recruiter_outreach.cli sync-jobs --source boards --boards data/boards.txt --interval 900
```

使用 API 来源时可指定 `--source adzuna` 或 `--source jooble`、重复 `--term "AI engineer"` 和 `--city Canada`；不指定来源时自动选择本地 `.env` 中已配置的 API 或提供的招聘板。重复运行会在 `data/jobs.sqlite3` 去重并维护首次/最近发现时间，工作簿写入 `output/latest_jobs.xlsx`。职位中提取的邮箱未经验证，不应据此直接发信。若招聘板接口不可用或配额用尽，当次同步报错，之前的 Excel 文件保留。

