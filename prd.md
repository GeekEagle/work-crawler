# PRD: Canada IT Recruiter Outreach Assistant

**Status:** Draft for review  
**Owner:** User  
**Version:** 0.1  
**Date:** 2026-10-23

## 1. Summary

Build a user-controlled web application that helps a job seeker discover relevant IT recruiter and hiring contacts in Canada, organize publicly available professional information, draft personalized outreach, and send messages only after explicit user approval and applicable consent/compliance checks.

The product is an outreach assistant, not an autonomous mass-mailing bot. It must not request, store, or operate the user's LinkedIn or Indeed passwords, bypass platform controls, scrape authenticated pages, evade rate limits, or send bulk unsolicited messages.

## 2. Problem

A job seeker needs a repeatable way to identify legitimate Canadian IT recruiting opportunities, prioritize relevant contacts, tailor a resume introduction, and track outreach. Manual research is time-consuming, while indiscriminate scraping and emailing create privacy, platform-policy, and anti-spam risks.

## 3. Goals

- Find relevant Canadian IT recruiting organizations and publicly listed recruiter contacts.
- Support targeting by location, role, technology, seniority, work authorization, and employment type.
- Import only data from permitted sources and preserve source attribution.
- Generate personalized email drafts using the user's approved resume and preferences.
- Require a human review and confirmation before every send or clearly defined batch.
- Maintain consent, opt-out, suppression, audit, and delivery records.
- Provide export and deletion controls for all user data.

## 4. Non-goals

- Finding “all” recruiters or guaranteeing complete market coverage.
- Buying, guessing, or enriching private email addresses.
- Scraping LinkedIn, Indeed, or other logged-in pages without explicit official API permission.
- Using user credentials, session cookies, CAPTCHA bypasses, proxy rotation, or browser automation to evade controls.
- Sending unsolicited bulk campaigns, deceptive messages, or repeated follow-ups after an opt-out.
- Automatically applying to jobs or impersonating the user.
- Making legal determinations about consent, immigration, employment eligibility, or Canadian anti-spam law.

## 5. Target users

### Primary user
A job seeker who wants to contact Canadian IT recruiters about legitimate interview opportunities.

### Secondary user
A career coach or authorized assistant working with one job seeker and operating under that user's approval.

## 6. Product principles

1. **Human-in-the-loop:** No contact is messaged without user review and confirmation.
2. **Permission before automation:** Prefer official APIs, user-provided data, or public business contact channels with documented terms.
3. **Data minimization:** Collect only information needed for discovery, relevance scoring, personalization, and audit.
4. **Traceability:** Store source URL, collection time, source type, and processing history for every contact.
5. **Respectful outreach:** Low volume, relevant messages, honest identity, clear purpose, and easy opt-out.
6. **Fail closed:** If source permission, recipient legitimacy, or send authorization is uncertain, do not collect or send.

## 7. Scope and requirements

### 7.1 User profile and resume

The user can:

- Enter name, location, work authorization status, target provinces/cities, target roles, technologies, seniority, salary expectations, availability, and preferred work arrangement.
- Upload a resume in PDF or DOCX format.
- Choose whether the resume may be attached, linked, or omitted.
- Edit a short professional introduction and approved email signature.
- Configure daily sending limits, quiet hours, and follow-up rules.

Requirements:

- Parse resume text locally or through a documented processor; retain the original only with user consent.
- Never infer protected characteristics or use them for targeting.
- Never send a resume without an explicit per-send or batch approval.

### 7.2 Contact discovery

Supported source types, in priority order:

1. User-imported contacts or CSV files.
2. Official, authorized APIs and partner feeds.
3. Public company career pages, agency pages, and recruiter contact pages where collection and use are permitted.
4. Manually entered contact details.

Each record must include:

- Contact name, organization, role, country/province/city when available.
- Public business email only when clearly published for professional contact or supplied by the user.
- Source URL, source type, collection timestamp, and confidence.
- Relevant job or recruiting context.
- Consent/permission status: unknown, user-supplied, explicit opt-in, public-business-contact, opted-out, or blocked.

The system must reject or flag:

- Personal emails not clearly intended for professional contact.
- Guessed email addresses.
- Password-protected or authenticated content collected without an approved integration.
- Duplicate, stale, invalid, disposable, or suppression-listed contacts.
- Contacts outside the configured Canadian targeting scope unless the user overrides it.

### 7.3 Relevance and prioritization

Score contacts using explainable signals:

- Match between recruiter/company focus and target role/technology.
- Canadian location and work arrangement fit.
- Recency and relevance of associated public job posting.
- Whether the contact is a recruiter, talent acquisition professional, agency contact, or hiring manager.
- Source confidence and permission status.

Do not rank based on protected attributes, inferred age, ethnicity, gender, disability, religion, or other sensitive traits.

### 7.4 Message drafting

Generate a draft containing:

- Honest sender identity and target role.
- One or two specific reasons the contact is relevant.
- Concise qualifications drawn only from the approved resume/profile.
- A clear interview or conversation request.
- Resume attachment/link only if approved.
- A professional signature and a simple opt-out instruction.

The draft must never:

- Claim prior contact, referral, employment authorization, or experience not provided by the user.
- Pretend to be a platform, recruiter, or employer.
- Use manipulative urgency, misleading subject lines, or bulk-template language that hides personalization.

### 7.5 Review and sending

Before sending, show a review queue with:

- Recipient, organization, source, source timestamp, and permission status.
- Full message and attachment/link preview.
- Why the contact was selected.
- Duplicate and previous-contact warnings.
- Compliance warnings and missing fields.

The user must explicitly approve:

- Each individual message, or
- A clearly displayed batch with a fixed recipient list, exact template variables, and a maximum batch size.

Sending requirements:

- Use the user's own approved email provider via OAuth or app password flow; never collect the mailbox password directly.
- Support provider rate limits and daily caps.
- Record message ID, timestamp, recipient, content hash, and delivery status.
- Automatically stop on provider errors, bounce spikes, spam warnings, or an opt-out.
- No automatic follow-up unless separately approved and only when no opt-out or negative response exists.

### 7.6 Inbox and response handling

Optional integrations may classify incoming replies into:

- Interested / interview request.
- Needs more information.
- Not a fit.
- Automated response.
- Opt-out / do not contact.
- Unclear; requires user review.

The system may draft replies but must not send them without user approval. Any opt-out must immediately add the sender and relevant organization/address to the suppression list.

## 8. Privacy, security, and compliance requirements

- Do not ask the user to provide LinkedIn or Indeed credentials.
- Do not store third-party platform session cookies or scrape authenticated content.
- Use official APIs only where the platform grants access and the integration terms permit the intended use.
- Encrypt stored resumes, access tokens, contact data, and message history at rest; use TLS in transit.
- Store OAuth tokens in a secrets manager and request the minimum scopes.
- Provide account export and permanent deletion.
- Define retention defaults, with user-configurable deletion for contacts, drafts, logs, and attachments.
- Maintain a global suppression list and check it immediately before every send.
- Display jurisdiction and consent warnings and require the user to confirm responsibility for lawful use.
- Obtain a qualified legal review before production use in Canada; the product must not represent itself as legal advice.

## 9. Proposed architecture

- **Frontend:** Web dashboard for profile, sources, review queue, sending, inbox, and settings.
- **Backend API:** Authentication, authorization, contact records, source provenance, scoring, drafts, approvals, suppression, and audit logs.
- **Ingestion workers:** Connect only to approved APIs, public pages, or user uploads; enforce robots/terms/rate policies and source-specific adapters.
- **Email service:** OAuth-based provider adapter with dry-run mode, throttling, bounce handling, and provider webhooks.
- **Storage:** Relational database for structured data; encrypted object storage for resumes; secrets manager for tokens.
- **Audit service:** Append-only event log for imports, edits, approvals, sends, opt-outs, deletions, and administrative access.

## 10. Core data entities

- `UserProfile`
- `ResumeVersion`
- `Source`
- `Contact`
- `RecruitingContext`
- `ConsentRecord`
- `SuppressionEntry`
- `MessageDraft`
- `SendApproval`
- `DeliveryEvent`
- `InboxEvent`
- `AuditEvent`

Every `Contact` must be linked to at least one `Source` or marked `user_supplied`.

## 11. MVP acceptance criteria

- User can create a profile and upload an approved resume.
- User can import a CSV and see validation errors without sending anything.
- User can add an approved public-source adapter and view provenance for every contact.
- System rejects guessed emails and blocks suppression-listed recipients.
- System generates a personalized draft using only approved profile/resume facts.
- User can edit and approve a single draft or a bounded batch.
- Dry-run mode shows exactly what would be sent.
- Sending requires OAuth authorization and enforces configurable caps.
- Opt-outs suppress future messages immediately.
- User can export and delete their data.
- Audit log shows who approved, what was sent, when, and to whom.

## 12. Success metrics

- Percentage of discovered contacts with valid provenance.
- Percentage of drafts approved without factual corrections.
- Interview/conversation response rate.
- Bounce and opt-out rates.
- Percentage of contacts blocked before send due to missing permission or suppression.
- Zero credential collection for LinkedIn/Indeed.
- Zero sends without recorded user approval.

## 13. Risks and mitigations

- **Platform restrictions:** Use official APIs or permitted public sources; disable an adapter when terms or access change.
- **Spam complaints:** Keep volume low, require approval, personalize, include opt-out, and stop on complaints.
- **Incorrect personalization:** Use source-linked facts and require review.
- **Sensitive data exposure:** Minimize fields, encrypt data, limit retention, and provide deletion.
- **False completeness:** Clearly label results as a curated set, not “all” Canadian recruiters.
- **Credential compromise:** OAuth and secrets management; never accept platform passwords.

## 14. Delivery phases

### Phase 1: Safe foundation
Profile, resume management, CSV/manual import, provenance, suppression list, draft generation, review queue, dry-run mode, and audit log.

### Phase 2: Authorized integrations
Email OAuth provider, delivery status, bounce/opt-out processing, and one approved public-source or official API adapter.

### Phase 3: Workflow improvements
Inbox classification, explainable ranking, reusable templates, analytics, and additional integrations after source-specific review.

### Phase 4: Production readiness
Security review, privacy review, legal review for Canadian outreach, load testing, incident response, and operational monitoring.

## 15. Open decisions

- Which email provider should be supported first?
- Will the user supply contact CSVs, or should the MVP include one approved public-source adapter?
- What daily send cap and review batch size are acceptable?
- Which Canadian provinces, cities, roles, and technologies are in the initial target profile?
- What retention period should apply to resumes, contacts, drafts, and delivery logs?

## Amendment: Spreadsheet-First Workflow

The MVP should produce an `.xlsx` workbook before any outreach. The workbook must contain a filterable `Recruiter Contacts` sheet and optional `Job Leads` sheet. Recommended columns are: `Include`, contact name, job title, company, email, province, city, recruiter type, target role tags, relevant job title, job URL, source URL, source type, collected time, email confidence, permission status, status, notes, last contacted time, opt-out, and do-not-contact reason.

The workbook must freeze headers, enable filters, preserve source URLs, include a README sheet, leave unknown emails blank, avoid guessed addresses, deduplicate normalized email/company pairs, and never send email merely because it was exported.

User workflow:

1. Generate the workbook from permitted sources.
2. User filters rows manually and marks selected rows `Include = Y`.
3. User re-imports the approved workbook.
4. System validates addresses, provenance, suppression status, and required fields.
5. System generates one personalized draft per approved row.
6. User reviews and approves each draft or a bounded batch.
7. System sends only approved messages and attaches the selected resume PDF.

Initial target-role filters should include machine learning engineer, software developer/SDE, data engineer, AI engineer, backend engineer, frontend engineer, full-stack engineer, DevOps/cloud engineer, QA/automation engineer, and other IT roles. Location scope is all Canadian provinces and territories, with filters for province, city, remote, hybrid, and onsite.

The system must not request LinkedIn or Indeed passwords, scrape authenticated pages, guess private email addresses, bypass platform controls, or send without explicit user approval. Discovery should use user-provided contacts, permitted public business contact pages, or officially authorized APIs.

## Amendment: LLM Integration and Automated Outreach

### LLM capabilities

The system may connect to a configurable LLM provider through an API adapter. The LLM can:

- Classify job postings and recruiter contacts by relevance.
- Extract role, technology, location, seniority, and work-arrangement information.
- Match job requirements against the user’s approved resume.
- Generate personalized subject lines and email drafts.
- Produce concise recruiter-specific explanations for why a contact was selected.
- Detect duplicate, low-quality, suspicious, or irrelevant contacts.
- Classify replies such as interested, rejected, automated response, or opt-out.

The LLM must only use approved user profile data, resume content, job-posting content, and contact/source metadata. It must not invent qualifications, employers, referrals, work authorization, availability, or prior conversations.

The user must be able to choose whether resume text and contact data may be sent to the LLM provider. Sensitive data should be minimized or redacted where possible. API keys must be stored server-side in a secrets manager and never exposed in the browser.

### Automated email modes

The system supports three modes:

1. **Draft-only:** Generate messages but never send them.
2. **Approval-required:** Send only after the user approves each message or a fixed batch.
3. **Controlled auto-send:** Automatically send only contacts that satisfy all configured rules:
   - The contact was selected by the user in the approved workbook or through an equivalent explicit approval action.
   - The contact has a valid public business email or user-supplied address.
   - The contact is not on the suppression or opt-out list.
   - The contact has not already been contacted within the configured cooldown period.
   - The message passes required-field, provenance, duplicate, and content checks.
   - The message is within the daily and per-campaign sending limits.
   - The selected resume PDF and sender identity are approved.

Controlled auto-send must have a prominent enable/disable switch, a dry-run preview, daily limits, quiet hours, automatic stop conditions, and a complete audit log. The system must stop sending when bounce rates, provider warnings, complaints, or opt-outs exceed configured thresholds.

The system must never auto-send to guessed addresses, private personal addresses, contacts with unknown permission status when the user has not explicitly enabled that category, or recipients who have opted out.

### Expanded AI-related target roles

Add the following role filters and aliases:

- Machine Learning Engineer
- AI Engineer
- Applied AI Engineer
- Generative AI Engineer
- LLM Engineer
- AI/ML Software Engineer
- Research Engineer
- Research Scientist
- Deep Learning Engineer
- NLP Engineer
- Natural Language Processing Scientist
- Computer Vision Engineer
- Speech and Audio AI Engineer
- Robotics / Autonomous Systems Engineer
- Reinforcement Learning Engineer
- MLOps Engineer
- ML Platform Engineer
- AI Infrastructure Engineer
- Model Serving / Inference Engineer
- Data and Machine Learning Engineer
- Data Scientist
- Applied Scientist
- AI Solutions Architect
- AI Solutions Engineer
- Machine Learning Platform Developer
- Prompt Engineer
- Retrieval-Augmented Generation Engineer
- AI Evaluation Engineer
- Responsible AI / AI Safety Engineer
- Knowledge Graph Engineer
- Recommender Systems Engineer
- Quantitative Machine Learning Engineer
- Edge AI / Embedded ML Engineer
- AI Product Engineer
- Technical AI Product Manager

Role matching should use both exact titles and skill-based signals such as Python, PyTorch, TensorFlow, scikit-learn, transformers, RAG, vector databases, model serving, Kubernetes, MLOps, NLP, computer vision, reinforcement learning, distributed training, and cloud ML platforms. Skill-based matching must be explainable and must not override the user’s manual selection rules.
