from __future__ import annotations

import os
from contextlib import closing
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from recruiter_outreach.job_alerts import parse_alert
from recruiter_outreach.job_excel import export_jobs_xlsx, export_xlsx, ids_from_reviewed_xlsx
from recruiter_outreach.job_matching import DEFAULT_PROFILE, match_job
from recruiter_outreach.job_sources import canadian_it_jobs
from recruiter_outreach.job_storage import all_jobs, connect, review_jobs, upsert_jobs
from recruiter_outreach.llm import LLMClient, LLMConfig
from recruiter_outreach.job_sync import DEFAULT_TERMS, SyncConfig, sync_once

load_dotenv()
st.set_page_config(page_title="加拿大 AI/IT 职位助手", layout="wide")
st.title("加拿大 AI/IT 职位助手")
st.caption("公开/授权职位来源 → SQLite 去重 → Excel 人工审核；不登录或抓取 LinkedIn 页面")

def read_jobs(database_path: str) -> list[dict]:
    with closing(connect(Path(database_path))) as database:
        return [job for job in all_jobs(database) if not job["is_demo"]]


def save_jobs(database_path: str, items: list[dict]) -> tuple[int, int]:
    with closing(connect(Path(database_path))) as database:
        return upsert_jobs(database, canadian_it_jobs(items))

with st.sidebar:
    st.header("同步设置")
    database_path = st.text_input("SQLite 路径", "data/jobs.sqlite3")
    output_path = st.text_input("Excel 输出", "output/latest_jobs.xlsx")
    terms_text = st.text_area("职位关键词（每行一个）", "\n".join(DEFAULT_TERMS), height=150)
    cities_text = st.text_input("地区（逗号分隔）", "Canada")
    source_options = ["adzuna", "jooble", "boards"]
    default_sources = []
    sources = st.multiselect("职位来源", source_options, default=default_sources)
    boards = st.text_area("招聘板：平台|公司|slug", placeholder="ashby|Company|slug\nlever|Company|slug", height=90)
    pages = st.number_input("Adzuna 页数", min_value=1, max_value=5, value=1)
    profile = st.text_area("本地职位匹配资料（不会自动发送）", DEFAULT_PROFILE, height=160)

st.header("1. 同步最新职位")
if st.button("立即同步"):
    try:
        config = SyncConfig(tuple(sources), tuple(x.strip() for x in terms_text.splitlines() if x.strip()), tuple(x.strip() for x in cities_text.split(",") if x.strip()), int(pages), boards, 900)
        result = sync_once(config, database_path, output_path)
        st.success(f"抓取 {result['fetched']} 条，新增 {result['inserted']} 条，更新 {result['updated']} 条")
    except Exception as exc:
        st.error(str(exc))

with st.expander("导入 LinkedIn / Indeed Job Alert 邮件"):
    st.caption("支持上传原始 .eml；不登录平台，不读取邮箱，职位链接和地点由邮件内容解析。")
    alert_files = st.file_uploader("Job Alert .eml", type=["eml"], accept_multiple_files=True)
    if st.button("解析上传的 Job Alert"):
        try:
            imported = [job for uploaded in alert_files or [] for job in parse_alert(uploaded.getvalue())]
            imported = [job for job in imported if job.get("title")]
            added, updated = save_jobs(database_path, imported)
            st.success(f"解析 {len(imported)} 条，新增 {added} 条，更新 {updated} 条")
        except Exception as exc:
            st.error(str(exc))

jobs = read_jobs(database_path)
pending = [job for job in jobs if job["review_state"] == "pending"]
kept = [job for job in jobs if job["review_state"] == "kept"]
rejected = [job for job in jobs if job["review_state"] == "rejected"]
st.header("2. Excel 人工审核")
st.write(f"职位总数 {len(jobs)} · 待审核 {len(pending)} · 人工保留 {len(kept)} · 人工剔除 {len(rejected)}")
if pending:
    st.download_button("下载待审核 Excel", export_xlsx(pending), "canada_it_jobs_review.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
review_file = st.file_uploader("上传删除不合适行后的 Excel", type=["xlsx"])
if review_file and st.button("确认应用人工审核"):
    try:
        exported, approved = ids_from_reviewed_xlsx(review_file)
        with closing(connect(Path(database_path))) as database:
            accepted, removed = review_jobs(database, exported, approved)
        st.success(f"保留 {accepted} 条，剔除 {removed} 条")
        st.rerun()
    except Exception as exc:
        st.error(str(exc))

st.header("3. 职位匹配结果")
if jobs:
    ranked = []
    for job in jobs:
        result = match_job(job, profile)
        ranked.append({"id": job["id"], "公司": job["company"], "职位": job["title"], "地点": job["location"], "分数": result["score"], "地点状态": result["location_status"], "审核状态": job["review_state"], "来源": job["source"], "链接": job["url"]})
    st.dataframe(sorted(ranked, key=lambda row: row["分数"], reverse=True), use_container_width=True)
    st.download_button("下载当前全部职位 Excel", export_jobs_xlsx(jobs), "latest_jobs.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("还没有职位；请先配置来源并同步。")

st.header("4. AI 分析（仅限人工保留职位）")
st.caption("只有你主动点击分析并勾选同意后，才会把选中职位及输入的资料发送到 LLM；不会发送邮件。")
if kept:
    selected = st.multiselect("选取职位", [job["id"] for job in kept], format_func=lambda ident: next(f"{job['company']} · {job['title']}" for job in kept if job["id"] == ident))
    question = st.text_input("问题", "哪些职位最适合我？请只基于提供的事实分析。")
    allow_llm = st.checkbox("我同意把选中的职位和上方资料发送给配置的 LLM")
    if st.button("分析选中职位", disabled=not selected or not allow_llm):
        try:
            import json

            context = [{key: job.get(key, "") for key in ("id", "title", "company", "location", "description", "url")} for job in kept if job["id"] in selected][:20]
            messages = [{"role": "system", "content": "只根据用户提供的职位与候选人信息分析；不得编造资质、邮箱或职位。"},
                        {"role": "user", "content": json.dumps({"profile": profile, "jobs": context, "question": question}, ensure_ascii=False)}]
            st.write(LLMClient(LLMConfig.from_env()).complete(messages))
        except Exception as exc:
            st.error(str(exc))
else:
    st.info("请先人工保留职位，再使用 AI 分析。")
