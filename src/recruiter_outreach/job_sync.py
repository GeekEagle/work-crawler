from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .job_excel import write_jobs_xlsx
from .job_sources import canadian_it_jobs, fetch_adzuna, fetch_board, fetch_jooble, parse_boards
from .job_storage import all_jobs, connect, upsert_jobs

DEFAULT_TERMS = [
    "machine learning engineer", "AI engineer", "software engineer",
    "LLM engineer", "data engineer", "MLOps engineer", "computer vision engineer",
]
DEFAULT_CITIES = ["Canada"]


@dataclass(frozen=True)
class SyncConfig:
    sources: tuple[str, ...]
    terms: tuple[str, ...]
    cities: tuple[str, ...]
    pages: int = 1
    boards: str = ""
    interval_seconds: int = 900


def _fetch(config: SyncConfig) -> list[dict]:
    jobs: list[dict] = []
    for source in config.sources:
        if source == "adzuna":
            jobs.extend(fetch_adzuna(list(config.terms), list(config.cities), pages=config.pages))
        elif source == "jooble":
            jobs.extend(fetch_jooble(list(config.terms), list(config.cities)))
        elif source == "boards":
            for kind, company, slug in parse_boards(config.boards):
                jobs.extend(fetch_board(kind, company, slug))
        else:
            raise ValueError(f"Unsupported job source: {source}")
    return canadian_it_jobs(jobs)


def sync_once(config: SyncConfig, database_path: str | Path, output: str | Path) -> dict:
    load_dotenv()
    jobs = _fetch(config)
    with connect(Path(database_path)) as database:
        inserted, updated = upsert_jobs(database, jobs)
        stored = [job for job in all_jobs(database) if not job["is_demo"]]
    write_jobs_xlsx(stored, output)
    return {"fetched": len(jobs), "inserted": inserted, "updated": updated, "stored": len(stored), "output": str(output)}


def watch(config: SyncConfig, database_path: str | Path, output: str | Path, once: bool = False) -> None:
    while True:
        result = sync_once(config, database_path, output)
        print(f"同步完成：抓取 {result['fetched']}，新增 {result['inserted']}，更新 {result['updated']}，工作簿 {result['output']}")
        if once:
            return
        time.sleep(config.interval_seconds)


def config_from_env(source_names: list[str], terms: list[str], cities: list[str], pages: int, boards: str, interval_seconds: int) -> SyncConfig:
    available = (
        ("adzuna", bool(os.getenv("ADZUNA_APP_ID") and os.getenv("ADZUNA_APP_KEY"))),
        ("jooble", bool(os.getenv("JOOBLE_API_KEY"))),
        ("boards", bool(boards)),
    )
    configured = tuple(source_names or [name for name, enabled in available if enabled])
    if not configured:
        raise ValueError("没有可用职位来源；请配置 API，或使用 --source boards 并提供 --boards")
    return SyncConfig(tuple(configured), tuple(terms or DEFAULT_TERMS), tuple(cities or DEFAULT_CITIES), pages, boards, interval_seconds)
