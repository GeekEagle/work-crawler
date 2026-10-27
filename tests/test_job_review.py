import io
import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

from recruiter_outreach.job_excel import export_xlsx, ids_from_reviewed_xlsx
from recruiter_outreach.job_sources import canadian_it_jobs
from recruiter_outreach.job_storage import all_jobs, connect, review_jobs, upsert_jobs


class ReviewTests(unittest.TestCase):
    def test_excel_deleted_row_remains_rejected_after_recrawl(self):
        with tempfile.TemporaryDirectory() as folder:
            database = connect(Path(folder) / "jobs.sqlite3")
            try:
                jobs = [dict(title=title, company="Example", location="Toronto, ON", source="Lever",
                             url=f"https://example.com/{index}")
                        for index, title in enumerate(("Software Engineer", "ML Engineer"))]
                upsert_jobs(database, jobs)
                rows = all_jobs(database)
                workbook = load_workbook(io.BytesIO(export_xlsx(rows)))
                workbook["Job Leads"].delete_rows(3)
                result = io.BytesIO()
                workbook.save(result)
                upload = type("Upload", (), {"getvalue": lambda self: result.getvalue()})()
                exported, kept = ids_from_reviewed_xlsx(upload)
                self.assertEqual(review_jobs(database, exported, kept), (1, 1))
                upsert_jobs(database, jobs)
                states = {row["review_state"] for row in all_jobs(database)}
                self.assertEqual(states, {"kept", "rejected"})
            finally:
                database.close()

    def test_only_explicit_canadian_it_locations(self):
        records = [dict(title="Full Stack Developer", location="Vancouver, BC"),
                   dict(title="ML Engineer", location="Remote - US only"),
                   dict(title="Marketing Manager", location="Toronto, ON")]
        self.assertEqual(canadian_it_jobs(records), records[:1])


if __name__ == "__main__":
    unittest.main()

