"""Local SQLite persistence for normalized job leads."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "data" / "jobs.sqlite3"
STATUSES = ("未处理", "感兴趣", "已投递", "面试中", "已拒绝", "不考虑")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def fingerprint(job: dict) -> str:
    """Stable identity: source type + company + position, not location or posting time."""
    company = _norm(str(job.get("company", "")))
    title = _norm(str(job.get("title", "")))
    if not company:
        company = _norm(str(job.get("url", "")))
    identity = "|".join((str(bool(job.get("is_demo"))), company, title))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def _ensure_schema(db: sqlite3.Connection) -> None:
    db.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT, location TEXT,
        description TEXT, url TEXT, source TEXT, posted TEXT, salary TEXT,
        job_type TEXT, remote TEXT, recruiter_email TEXT NOT NULL DEFAULT '',
        review_state TEXT NOT NULL DEFAULT 'pending', is_demo INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT '未处理', notes TEXT NOT NULL DEFAULT '',
        saved INTEGER NOT NULL DEFAULT 0, first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL, fetched_at TEXT NOT NULL DEFAULT ''
    )""")
    columns = {row[1] for row in db.execute("PRAGMA table_info(jobs)")}
    migrations = {
        "recruiter_email": "ALTER TABLE jobs ADD COLUMN recruiter_email TEXT NOT NULL DEFAULT ''",
        "review_state": "ALTER TABLE jobs ADD COLUMN review_state TEXT NOT NULL DEFAULT 'pending'",
        "fetched_at": "ALTER TABLE jobs ADD COLUMN fetched_at TEXT NOT NULL DEFAULT ''",
    }
    for name, statement in migrations.items():
        if name not in columns:
            db.execute(statement)
    db.execute("UPDATE jobs SET fetched_at=COALESCE(NULLIF(fetched_at, ''), last_seen, first_seen)")


def _migrate_identities(db: sqlite3.Connection) -> None:
    rows = [dict(row) for row in db.execute("SELECT * FROM jobs")]
    for row in rows:
        old_id = row["id"]
        new_id = fingerprint(row)
        if new_id == old_id:
            continue
        target = db.execute("SELECT id, description, source, url FROM jobs WHERE id=?", (new_id,)).fetchone()
        if target:
            description = row.get("description") or ""
            if len(description) > len(target["description"] or ""):
                db.execute("UPDATE jobs SET description=?, url=? WHERE id=?", (description, row.get("url", ""), new_id))
            merged_source = ", ".join(dict.fromkeys(filter(None, ((target["source"] or "") + ", " + (row.get("source") or "")).split(", "))))
            db.execute("UPDATE jobs SET source=? WHERE id=?", (merged_source, new_id))
            db.execute("DELETE FROM jobs WHERE id=?", (old_id,))
        else:
            db.execute("UPDATE jobs SET id=? WHERE id=?", (new_id, old_id))


def connect(path: Path = DB) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    _ensure_schema(db)
    _migrate_identities(db)
    db.commit()
    return db


def upsert_jobs(db: sqlite3.Connection, jobs: list[dict]) -> tuple[int, int]:
    now = _now()
    inserted = skipped = 0
    for job in jobs:
        if not job.get("title"):
            continue
        ident = fingerprint(job)
        prior = db.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone()
        if prior:
            skipped += 1
        else:
            db.execute("""INSERT INTO jobs(id,title,company,location,description,url,source,posted,
                       salary,job_type,remote,recruiter_email,is_demo,first_seen,last_seen,fetched_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (ident, job.get("title", ""), job.get("company", ""), job.get("location", ""),
                        job.get("description", ""), job.get("url", ""), job.get("source", ""), job.get("posted", ""),
                        job.get("salary", ""), job.get("job_type", ""), job.get("remote", ""),
                        job.get("recruiter_email", ""), int(bool(job.get("is_demo"))), now, now, now))
            inserted += 1
    db.commit()
    return inserted, skipped


def all_jobs(db: sqlite3.Connection) -> list[dict]:
    return [dict(j) for j in db.execute("SELECT * FROM jobs ORDER BY first_seen DESC")]


def update_user_field(db: sqlite3.Connection, ident: str, field: str, value: str | int) -> None:
    if field not in ("status", "notes", "saved"):
        raise ValueError("不允许修改该字段")
    if field == "status" and value not in STATUSES:
        raise ValueError("无效求职状态")
    db.execute(f"UPDATE jobs SET {field}=? WHERE id=?", (value, ident))
    db.commit()


def review_jobs(db: sqlite3.Connection, exported: set[str], kept: set[str]) -> tuple[int, int]:
    known = {row[0] for row in db.execute("SELECT id FROM jobs WHERE is_demo=0")}
    if not exported or not kept <= exported or not exported <= known:
        raise ValueError("审核文件与当前数据库不匹配；请重新下载 Excel")
    db.executemany("UPDATE jobs SET review_state='kept' WHERE id=?", [(ident,) for ident in kept])
    rejected = exported - kept
    db.executemany("UPDATE jobs SET review_state='rejected' WHERE id=?", [(ident,) for ident in rejected])
    db.commit()
    return len(kept), len(rejected)


