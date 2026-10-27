from __future__ import annotations

import io
from pathlib import Path

from openpyxl import Workbook

JOB_FIELDS = [
    "id", "company", "title", "location", "salary", "recruiter_email",
    "source", "url", "description", "posted", "status", "notes", "first_seen", "last_seen",
]


def safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def export_jobs_xlsx(items: list[dict]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Job Leads"
    sheet.append(JOB_FIELDS)
    for item in items:
        sheet.append([safe_cell(item.get(field, "")) for field in JOB_FIELDS])
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for column in sheet.columns:
        width = min(max(len(str(cell.value or "")) for cell in column) + 2, 45)
        sheet.column_dimensions[column[0].column_letter].width = width
    readme = workbook.create_sheet("README")
    readme.append(["加拿大职位同步结果"])
    readme.append(["数据来自已配置的公开/授权职位来源；请人工核对职位链接和联系方式。"])
    readme.append(["导出不会发送邮件。职位排序按首次发现时间倒序。"])
    readme.column_dimensions["A"].width = 100
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def write_jobs_xlsx(items: list[dict], output: str | Path) -> Path:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(export_jobs_xlsx(items))
    return output
