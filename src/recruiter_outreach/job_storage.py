"""Local SQLite persistence; no account or cloud database is required."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB = Path(__file__).resolve().parent / "data" / "jobs.sqlite3"
STATUSES = ("未处理", "感兴趣", "已投递", "面试中", "已拒绝", "不考虑")


def connect(path: Path = DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT, location TEXT,
        description TEXT, url TEXT, source TEXT, posted TEXT, salary TEXT,
        job_type TEXT, remote TEXT, recruiter_email TEXT NOT NULL DEFAULT '',
        review_state TEXT NOT NULL DEFAULT 'pending', is_demo INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT '未处理', notes TEXT NOT NULL DEFAULT '',
        saved INTEGER NOT NULL DEFAULT 0, first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL
    )""")
    columns = {row[1] for row in db.execute("PRAGMA table_info(jobs)")}
    if "recruiter_email" not in columns:
        db.execute("ALTER TABLE jobs ADD COLUMN recruiter_email TEXT NOT NULL DEFAULT ''")
    if "review_state" not in columns:
        db.execute("ALTER TABLE jobs ADD COLUMN review_state TEXT NOT NULL DEFAULT 'pending'")
    db.commit()
    return db


def fingerprint(job: dict) -> str:
    def norm(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", (value or "").lower())
    def canonical_location(value: str) -> str:
        location = (value or "").lower().replace("montréal", "montreal")
        for long, short in (("ontario", "on"), ("british columbia", "bc"), ("quebec", "qc"),
                            ("québec", "qc"), ("alberta", "ab")):
            location = re.sub(r"\b" + re.escape(long) + r"\b", short, location)
        location = re.sub(r"\bcanada\b", "", location)
        return norm(location)
    # Never mix fake demo rows with live ads.
    identity = "|".join((str(bool(job.get("is_demo"))), norm(job.get("company", "")),
                         norm(job.get("title", "")), canonical_location(job.get("location", ""))))
    if not norm(job.get("company", "")):
        identity += "|" + norm(job.get("url", ""))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def upsert_jobs(db: sqlite3.Connection, jobs: list[dict]) -> tuple[int, int]:
    now = datetime.now(timezone.utc).isoformat()
    inserted = updated = 0
    for job in jobs:
        if not job.get("title"):
            continue
        ident = fingerprint(job)
        prior = db.execute("SELECT id, description, url, source, salary, recruiter_email FROM jobs WHERE id=?", (ident,)).fetchone()
        if prior:
            description = job.get("description", "") if len(job.get("description", "")) > len(prior["description"] or "") else prior["description"]
            url = job.get("url") if not prior["url"] or len(job.get("description", "")) > len(prior["description"] or "") else prior["url"]
            source = ", ".join(dict.fromkeys(filter(None, (prior["source"] + ", " + job.get("source", "")).split(", "))))
            db.execute("""UPDATE jobs SET description=?, url=?, source=?, salary=?, recruiter_email=?, last_seen=? WHERE id=?""",
                       (description, url, source, job.get("salary") or prior["salary"],
                        job.get("recruiter_email") or prior["recruiter_email"], now, ident))
            updated += 1
        else:
            db.execute("""INSERT INTO jobs(id,title,company,location,description,url,source,posted,
                       salary,job_type,remote,recruiter_email,is_demo,first_seen,last_seen)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (ident, job.get("title", ""), job.get("company", ""), job.get("location", ""),
                        job.get("description", ""), job.get("url", ""), job.get("source", ""), job.get("posted", ""),
                        job.get("salary", ""), job.get("job_type", ""), job.get("remote", ""),
                        job.get("recruiter_email", ""), int(bool(job.get("is_demo"))), now, now))
            inserted += 1
    db.commit()
    return inserted, updated


def all_jobs(db: sqlite3.Connection) -> list[dict]:
    return [dict(j) for j in db.execute("SELECT * FROM jobs ORDER BY first_seen DESC")]


def update_user_field(db: sqlite3.Connection, ident: str, field: str, value: str | int) -> None:
    if field not in ("status", "notes", "saved"):
        raise ValueError("不允许修改该字段")
    if field == "status" and value not in STATUSES:
        raise ValueError("无效求职状态")
    db.execute(f"UPDATE jobs SET {field}=? WHERE id=?", (value, ident))
    db.commit()


def delete_jobs(db: sqlite3.Connection, identifiers: set[str]) -> int:
    if not identifiers:
        return 0
    before = db.total_changes
    db.executemany("DELETE FROM jobs WHERE id=?", [(ident,) for ident in identifiers])
    db.commit()
    return db.total_changes - before


def review_jobs(db: sqlite3.Connection, exported: set[str], kept: set[str]) -> tuple[int, int]:
    known = {row[0] for row in db.execute("SELECT id FROM jobs WHERE is_demo=0")}
    if not exported or not kept <= exported or not exported <= known:
        raise ValueError("审核文件与当前数据库不匹配；请重新下载 Excel")
    db.executemany("UPDATE jobs SET review_state='kept' WHERE id=?", [(ident,) for ident in kept])
    rejected = exported - kept
    db.executemany("UPDATE jobs SET review_state='rejected' WHERE id=?", [(ident,) for ident in rejected])
    db.commit()
    return len(kept), len(rejected)
