import tempfile
import unittest
from pathlib import Path

from recruiter_outreach.job_matching import DEFAULT_PROFILE, classify_location, match_job
from recruiter_outreach.job_sources import demo_jobs, parse_boards
from recruiter_outreach.job_storage import all_jobs, connect, fingerprint, update_user_field, upsert_jobs


class MatchingTests(unittest.TestCase):
    def test_location_canada(self):
        self.assertEqual(classify_location("Toronto, Ontario, Canada"), "canada")
        self.assertEqual(classify_location("Vancouver, BC"), "canada")
        self.assertEqual(classify_location("Remote - US only"), "incompatible")
        self.assertEqual(classify_location("Remote"), "unknown")

    def test_profile_scores_video_and_inference_roles(self):
        jobs = demo_jobs()
        scores = {job["title"]: match_job(job, DEFAULT_PROFILE)["score"] for job in jobs}
        self.assertGreater(scores["Computer Vision Engineer"], scores["AI Research Scientist"])
        self.assertGreater(scores["ML Inference Engineer"], scores["ML Platform Engineer"] - 20)
        bad = match_job(jobs[-1], DEFAULT_PROFILE)
        self.assertEqual(bad["location_status"], "incompatible")
        self.assertTrue(any("美国" in warning or "加拿大" in warning for warning in bad["flags"]))

    def test_incomplete_jd_flagged(self):
        job = {"title": "Machine Learning Engineer", "location": "Toronto", "description": "Python",
               "source": "Adzuna"}
        self.assertIn("初评", match_job(job, DEFAULT_PROFILE)["confidence"])
        job["source"] = "Adzuna, Jooble"
        job["description"] = "Python and PyTorch, " * 20
        self.assertIn("不完整", match_job(job, DEFAULT_PROFILE)["confidence"])

    def test_board_input(self):
        self.assertEqual(parse_boards("ashby|Example|example-slug"), [("ashby", "Example", "example-slug")])
        with self.assertRaises(ValueError):
            parse_boards("other|Example|x")

    def test_dedupe_preserves_manual_state(self):
        with tempfile.TemporaryDirectory() as folder:
            db = connect(Path(folder) / "jobs.sqlite3")
            try:
                base = dict(title="ML Engineer", company="Example", location="Toronto, Ontario, Canada",
                            description="Python", source="Adzuna", url="https://example.com/a")
                one = dict(base, location="Toronto, ON", source="Lever", description="Python, PyTorch and inference")
                self.assertEqual(fingerprint(base), fingerprint(one))
                self.assertEqual(upsert_jobs(db, [base]), (1, 0))
                row_id = all_jobs(db)[0]["id"]
                update_user_field(db, row_id, "status", "已投递")
                update_user_field(db, row_id, "saved", 1)
                self.assertEqual(upsert_jobs(db, [one]), (0, 1))
                row = all_jobs(db)[0]
                self.assertEqual(row["status"], "已投递")
                self.assertEqual(row["saved"], 1)
                self.assertIn("PyTorch", row["description"])
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

