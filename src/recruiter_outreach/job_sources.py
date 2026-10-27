"""Job source adapters. All endpoints are published provider APIs, not LinkedIn scraping."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests


TIMEOUT = 18
UA = "work-assistant/0.1 (personal Canadian job search)"
IT_TITLE = re.compile(r"\b(software|developer|engineer|programmer|full[ -]?stack|front[ -]?end|back[ -]?end|"
                      r"machine learning|\bml\b|\bai\b|algorithm|data scientist|data engineer|"
                      r"devops|sre|cloud|security|computer vision|\bit\b|platform|mobile|"
                      r"android|ios|qa|quality assurance|systems administrator|data analyst|"
                      r"network administrator|ux designer|it support)\b", re.I)
CANADA_LOCATION = re.compile(r"\b(canada|ontario|quebec|québec|alberta|british columbia|"
                             r"toronto|vancouver|montreal|montréal|ottawa|calgary|edmonton|"
                             r"waterloo|kitchener|winnipeg|halifax|victoria|saskatoon|regina|"
                             r"on|bc|qc|ab|mb|ns|nb|sk|nl|pe)\b", re.I)


def canadian_it_jobs(items: list[dict]) -> list[dict]:
    return [job for job in items if IT_TITLE.search(job.get("title", ""))
            and CANADA_LOCATION.search(job.get("location", ""))
            and not job.get("is_demo")]


def _get(url: str, params: dict | None = None) -> Any:
    response = requests.get(url, params=params, headers={"User-Agent": UA, "Accept": "application/json"}, timeout=TIMEOUT)
    if not response.ok:
        raise RuntimeError(f"API HTTP {response.status_code}（请检查密钥、额度或招聘板 slug）")
    return response.json()


def _item(**fields: Any) -> dict:
    defaults = dict(title="", company="", location="", description="", url="", source="", posted="",
                    salary="", job_type="", remote="", recruiter_email="", is_demo=False)
    defaults.update(fields)
    if not defaults.get("recruiter_email"):
        emails = re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", str(defaults.get("description") or ""), re.I)
        defaults["recruiter_email"] = emails[0] if emails else ""
    return {key: str(value).strip() if key != "is_demo" and value is not None else (bool(value) if key == "is_demo" else "")
            for key, value in defaults.items()}


def fetch_adzuna(terms: list[str], cities: list[str], pages: int = 1) -> list[dict]:
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        raise ValueError("请在 .env 配置 ADZUNA_APP_ID 和 ADZUNA_APP_KEY")
    jobs = []
    for term in terms:
        for city in cities:
            for page in range(1, pages + 1):
                data = _get(f"https://api.adzuna.com/v1/api/jobs/ca/search/{page}", {
                    "app_id": app_id, "app_key": app_key, "what": term, "where": city,
                    "results_per_page": 30, "sort_by": "date", "content-type": "application/json",
                })
                for j in data.get("results", []):
                    salary = ""
                    if j.get("salary_min") or j.get("salary_max"):
                        minimum, maximum = j.get("salary_min") or "?", j.get("salary_max") or "?"
                        suffix = "（平台预测）" if j.get("salary_is_predicted") else "（来源标注）"
                        salary = f"{minimum}–{maximum} CAD{suffix}"
                    jobs.append(_item(title=j.get("title", ""), company=j.get("company", {}).get("display_name", ""),
                                      location=j.get("location", {}).get("display_name", city),
                                      description=j.get("description", ""), url=j.get("redirect_url", ""),
                                      source="Adzuna", posted=j.get("created", ""), salary=salary,
                                      job_type=j.get("contract_type", "")))
    return jobs


def fetch_jooble(terms: list[str], cities: list[str]) -> list[dict]:
    key = os.getenv("JOOBLE_API_KEY")
    if not key:
        raise ValueError("请在 .env 配置 JOOBLE_API_KEY")
    base = os.getenv("JOOBLE_BASE_URL", "https://ca.jooble.org").rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme != "https" or not (parsed.hostname == "jooble.org" or (parsed.hostname or "").endswith(".jooble.org")):
        raise ValueError("JOOBLE_BASE_URL 必须是 Jooble 官方的 https 域名")
    jobs = []
    for term in terms:
        for city in cities:
            response = requests.post(f"{base}/api/{key}", json={"keywords": term, "location": city, "page": "1"},
                                     headers={"User-Agent": UA, "Content-Type": "application/json"}, timeout=TIMEOUT)
            if not response.ok:
                raise RuntimeError(f"Jooble API HTTP {response.status_code}（检查区域 Key 和配额）")
            for j in response.json().get("jobs", []):
                jobs.append(_item(title=j.get("title", ""), company=j.get("company", ""),
                                  location=j.get("location", city), description=j.get("snippet", ""),
                                  url=j.get("link", ""), source="Jooble", posted=j.get("updated", ""),
                                  salary=j.get("salary", ""), job_type=j.get("type", "")))
    return jobs


def parse_boards(config: str) -> list[tuple[str, str, str]]:
    """Lines: provider|company display name|public board slug."""
    entries = []
    for lineno, line in enumerate(config.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3 or parts[0].lower() not in {"ashby", "lever", "greenhouse"}:
            raise ValueError(f"招聘板第 {lineno} 行不正确；格式为 ashby|公司名称|slug")
        kind, company, slug = parts
        if not company or not slug or not all(ch.isalnum() or ch in "-_" for ch in slug):
            raise ValueError(f"招聘板第 {lineno} 行公司名或 slug 无效")
        entries.append((kind.lower(), company, slug))
    return entries


def fetch_board(kind: str, company: str, slug: str) -> list[dict]:
    if kind == "ashby":
        data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", {"includeCompensation": "true"})
        jobs = []
        for j in data.get("jobs", []):
            if not j.get("isListed", True):
                continue
            address = j.get("address") or {}
            country = (address.get("postalAddress") or {}).get("addressCountry") or ""
            location = ", ".join(x for x in [j.get("location", ""), country] if x)
            pay = j.get("compensation") or {}
            jobs.append(_item(title=j.get("title", ""), company=company, location=location,
                              description=j.get("descriptionPlain", ""), url=j.get("jobUrl", ""), source="Ashby",
                              posted=j.get("publishedAt", ""),
                              salary=pay.get("scrapeableCompensationSalarySummary", ""),
                              job_type=j.get("employmentType", ""), remote=j.get("workplaceType", "")))
        return jobs
    if kind == "lever":
        data = _get(f"https://api.lever.co/v0/postings/{slug}", {"mode": "json", "limit": 100})
        jobs = []
        for j in data:
            categories = j.get("categories") or {}
            locs = j.get("allLocations") or [categories.get("location", "")]
            jobs.append(_item(title=j.get("text", ""), company=company, location=", ".join(filter(None, locs)),
                              description=j.get("descriptionPlain", "") or j.get("description", ""),
                              url=j.get("hostedUrl", ""), source="Lever", job_type=categories.get("commitment", ""),
                              remote=categories.get("workplaceType", "")))
        return jobs
    if kind == "greenhouse":
        data = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", {"content": "true"})
        jobs = []
        for j in data.get("jobs", []):
            jobs.append(_item(title=j.get("title", ""), company=company,
                              location=(j.get("location") or {}).get("name", ""),
                              description=j.get("content", ""), url=j.get("absolute_url", ""),
                              source="Greenhouse", posted=j.get("updated_at", "")))
        return jobs
    raise ValueError("不支持此招聘板类型")


def demo_jobs() -> list[dict]:
    """Synthetic records only. They are NEVER represented as live job ads."""
    today = datetime.now(timezone.utc).date().isoformat()
    samples = [
        ("Computer Vision Engineer", "演示公司 A", "Toronto, ON, Canada", "Develop video understanding, OpenCV and PyTorch pipelines. Python, GPU inference, Docker. 3+ years. Hybrid.", "Hybrid"),
        ("ML Inference Engineer", "演示公司 B", "Vancouver, BC, Canada", "Optimize PyTorch inference and Triton, NVIDIA GPUs, distributed services, model serving, Python.", "OnSite"),
        ("Applied AI Engineer", "演示公司 C", "Waterloo, ON, Canada", "Build computer vision solutions and Python backend services using deep learning, deployment, API design.", "Hybrid"),
        ("AI Research Scientist", "演示公司 D", "Montréal, QC, Canada", "PhD required. Research generative AI models and publish papers. Advanced French required.", "OnSite"),
        ("Backend Python Engineer", "演示公司 E", "Ottawa, ON, Canada", "Develop Python microservices, Redis queue workers, performance profiling, containers and APIs.", "Remote"),
        ("ML Platform Engineer", "演示公司 F", "Remote - US only", "US work authorization required. Build ML infrastructure and GPU clusters.", "Remote"),
    ]
    return [_item(title=title, company=company, location=location, description=desc, source="演示数据",
                  posted=today, remote=remote, is_demo=True) for title, company, location, desc, remote in samples]
