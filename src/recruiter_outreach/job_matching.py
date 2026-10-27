"""Explainable ranking. Scores are priorities for review, NOT hiring probabilities."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone


DEFAULT_PROFILE = """Python PyTorch OpenCV computer vision video processing image restoration
watermark detection tracking object detection deep learning AI inference GPU CUDA NVIDIA Triton
model serving batch inference distributed workers Redis queues microservices Docker
performance optimization deployment backend APIs"""

CITY_GROUPS = {
    "Toronto / GTA": ("toronto", "mississauga", "markham", "scarborough", "brampton", "richmond hill", "north york", "oakville"),
    "Waterloo / Kitchener": ("waterloo", "kitchener", "cambridge"),
    "Vancouver / BC": ("vancouver", "burnaby", "richmond", "surrey", "victoria"),
    "Montréal / Québec": ("montreal", "montréal", "quebec city", "québec city"),
    "Ottawa": ("ottawa", "kanata"),
    "Calgary / Edmonton": ("calgary", "edmonton"),
}
CANADA_TERMS = ("canada", "ontario", "british columbia", "québec", "quebec", "alberta", "manitoba",
                "nova scotia", "saskatchewan", "new brunswick", "toronto", "waterloo", "kitchener",
                "vancouver", "burnaby", "montreal", "montréal", "ottawa", "calgary", "edmonton",
                "winnipeg", "halifax", "victoria")
SKILL_TERMS = {
    "Python": ("python",), "PyTorch": ("pytorch",), "Computer Vision": ("computer vision", "opencv", "cv engineer"),
    "Video AI": ("video", "vision-language", "multimodal"), "GPU / CUDA": ("gpu", "cuda", "nvidia"),
    "Inference": ("inference", "serving", "onnx", "triton"), "Distributed": ("distributed", "kafka", "redis", "queue"),
    "Backend": ("microservice", "backend", "api", "fastapi"), "Deployment": ("docker", "kubernetes", "deploy"),
    "Deep Learning": ("deep learning", "neural network", "machine learning", "mlops", "llm"),
}
PREFERRED_TITLES = (
    "computer vision", "machine learning", "ml engineer", "ai engineer", "ai infrastructure",
    "inference", "applied ai", "ml platform", "mlops", "video", "backend python", "python engineer",
    "software engineer", "deep learning", "gpu", "model serving",
)
STRONG_TITLES = ("computer vision", "ml inference", "machine learning", "ai infrastructure", "video ai")
MUST_REVIEW = (
    (r"\b(us|united states) (citizen|work authorization|only)\b|\bus[- ]only\b", "岗位可能只接受美国工作资格"),
    (r"\b(canadian citizens? only|citizenship required)\b", "可能要求加拿大公民身份"),
    (r"\b(security clearance|secret clearance)\b", "可能需要安全审查"),
    (r"\b(ph\.?d\.? required|must have a phd)\b", "明确要求博士学位"),
    (r"\b(french required|fluent in french|bilingual french)\b", "可能要求法语能力"),
)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def terms_in(text: str, keywords: tuple[str, ...] | list[str]) -> bool:
    haystack = " " + text.lower() + " "
    return any(re.search(r"(?<!\w)" + re.escape(word.lower()) + r"(?!\w)", haystack) for word in keywords)


def classify_location(location: str) -> str:
    """canada / incompatible / unknown. Plain 'Remote' is never assumed Canada-eligible."""
    loc = location.lower()
    if terms_in(loc, CANADA_TERMS) or re.search(r"\b(on|bc|qc|ab|ns|mb|sk|nb|pe|nl)\b", loc):
        return "canada"
    if any(term in loc for term in ("us only", "usa only", "united states only", "remote - us", "remote, us")):
        return "incompatible"
    if not loc or "remote" in loc or "worldwide" in loc:
        return "unknown"
    return "incompatible"


def match_job(job: dict, profile: str, years: int | None = None) -> dict:
    title = clean(job.get("title", ""))
    desc = clean(job.get("description", ""))
    loc = clean(job.get("location", ""))
    joined = f"{title} {desc}"
    low = joined.lower()
    low_profile = profile.lower()
    location_status = classify_location(loc)

    listed_skills = [skill for skill, variants in SKILL_TERMS.items() if terms_in(low, variants)]
    profile_skills = [skill for skill, variants in SKILL_TERMS.items() if terms_in(low_profile, variants)]
    common = [skill for skill in listed_skills if skill in profile_skills]
    missing = [skill for skill in listed_skills if skill not in profile_skills]
    skill = round(100 * len(common) / max(len(listed_skills), 1)) if listed_skills else 45

    title_match = terms_in(title, PREFERRED_TITLES)
    responsibility = 90 if terms_in(title, STRONG_TITLES) else 75 if title_match else 35
    if terms_in(low, ("video", "inference", "computer vision", "pytorch", "triton")):
        responsibility = min(100, responsibility + 10)

    experience = 70  # Unknown years are not an automatic rejection.
    years_required = [int(x) for x in re.findall(r"\b(\d{1,2})\+?\s*(?:years|yrs)\b", low)]
    needed = max(years_required, default=None)
    if years and needed is not None:
        experience = 85 if years >= needed else max(20, 75 - 15 * (needed - years))

    place = 100 if location_status == "canada" else 40 if location_status == "unknown" else 0
    growth = 60  # No made-up salary / promotion estimates.
    if job.get("salary"):
        growth += 10  # Salary is disclosed, not necessarily attractive.

    score = round(.30 * skill + .25 * experience + .25 * responsibility + .10 * place + .10 * growth)
    flags = [label for pattern, label in MUST_REVIEW if re.search(pattern, low, re.I)]
    if location_status == "incompatible":
        flags.insert(0, "地点不在加拿大或明确限制在其他国家")
    elif location_status == "unknown":
        flags.insert(0, "尚不能确认该 Remote 职位允许在加拿大工作")
    if needed and years is None:
        flags.append(f"职位提到 {needed} 年经验；你的年限尚未填写")
    elif needed and years and needed > years:
        flags.append(f"职位提到 {needed} 年经验，可能高于当前配置")

    # Aggregators only return snippets; no score should pretend full JD was read.
    source_labels = {item.strip() for item in job.get("source", "").split(",")}
    incomplete = bool(source_labels & {"Adzuna", "Jooble"}) or len(desc) < 180
    return dict(score=score, listed_skills=listed_skills, matched_skills=common,
                missing_skills=missing, flags=flags, location_status=location_status,
                confidence="初评（职位信息不完整）" if incomplete else "基于较完整 JD 的初评",
                evidence=f"命中技能 {len(common)}/{len(listed_skills)}，职能方向 {'较匹配' if title_match else '待核对'}")
