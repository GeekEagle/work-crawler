from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from typing import Any

ROLE_TAGS = [
    "machine_learning_engineer", "ai_engineer", "applied_ai_engineer",
    "generative_ai_engineer", "llm_engineer", "ai_ml_software_engineer",
    "research_engineer", "research_scientist", "deep_learning_engineer",
    "nlp_engineer", "computer_vision_engineer", "speech_audio_ai_engineer",
    "robotics_autonomous_systems_engineer", "reinforcement_learning_engineer",
    "mlops_engineer", "ml_platform_engineer", "ai_infrastructure_engineer",
    "model_serving_inference_engineer", "data_ml_engineer", "data_scientist",
    "applied_scientist", "ai_solutions_architect", "ai_solutions_engineer",
    "prompt_engineer", "rag_engineer", "ai_evaluation_engineer",
    "responsible_ai_engineer", "knowledge_graph_engineer",
    "recommender_systems_engineer", "edge_ai_engineer", "ai_product_engineer",
    "software_developer", "backend_engineer", "frontend_engineer",
    "full_stack_engineer", "devops_cloud_engineer", "qa_automation_engineer",
]

CONTACT_HEADERS = [
    "Include", "Contact Name", "Job Title", "Company", "Email", "Phone",
    "Province", "City", "Recruiter Type", "Target Role Tags",
    "Relevant Job Title", "Job URL", "Source URL", "Source Type",
    "Collected At", "Email Confidence", "Permission Status", "Status",
    "Notes", "Last Contacted At", "Opt Out", "Do Not Contact Reason",
]
JOB_HEADERS = [
    "Include", "Job Title", "Company", "Location", "Province", "City",
    "Work Arrangement", "Employment Type", "Technology Keywords", "Seniority",
    "Job URL", "Company URL", "Recruiter Contact", "Source URL",
    "Collected At", "Posting Date", "Status", "Notes",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Contact:
    contact_name: str = ""
    job_title: str = ""
    company: str = ""
    email: str = ""
    phone: str = ""
    province: str = ""
    city: str = ""
    recruiter_type: str = ""
    target_role_tags: str = ""
    relevant_job_title: str = ""
    job_url: str = ""
    source_url: str = ""
    source_type: str = "user_supplied"
    collected_at: str = ""
    email_confidence: str = "unknown"
    permission_status: str = "unknown"
    status: str = "new"
    notes: str = ""
    last_contacted_at: str = ""
    opt_out: str = "N"
    do_not_contact_reason: str = ""
    include: str = ""

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "Contact":
        aliases = {
            "Contact Name": "contact_name", "Job Title": "job_title", "Company": "company",
            "Email": "email", "Source URL": "source_url", "Source Type": "source_type",
            "Target Role Tags": "target_role_tags", "Relevant Job Title": "relevant_job_title",
            "Permission Status": "permission_status", "Email Confidence": "email_confidence",
            "Include": "include", "Opt Out": "opt_out", "Status": "status",
        }
        normalized = {}
        valid = {field.name for field in fields(cls)}
        for key, value in row.items():
            name = aliases.get(key, key).strip().lower().replace(" ", "_")
            if name in valid:
                normalized[name] = "" if value is None else str(value).strip()
        if not normalized.get("collected_at"):
            normalized["collected_at"] = now_iso()
        return cls(**normalized)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Draft:
    recipient: str
    subject: str
    body: str
    company: str = ""
    source_url: str = ""
    resume_path: str = ""
    approved: bool = False
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
