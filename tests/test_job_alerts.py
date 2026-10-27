import unittest

from recruiter_outreach.job_alerts import parse_alert


class AlertImportTests(unittest.TestCase):
    def test_parse_linkedin_alert(self):
        raw = b"""From: jobs-noreply@linkedin.com\nSubject: Job alert\nContent-Type: text/html; charset=utf-8\n\n<html><body><a href='https://www.linkedin.com/jobs/view/123'>Machine Learning Engineer</a><p>Example Corp | Toronto, Ontario, Canada | CA$120,000 - CA$150,000</p></body></html>"""
        jobs = parse_alert(raw)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Machine Learning Engineer")
        self.assertEqual(jobs[0]["source"], "LinkedIn Job Alert")
        self.assertIn("linkedin.com/jobs/view", jobs[0]["url"])

    def test_parse_indeed_alert(self):
        raw = b"""From: alert@indeed.com\nSubject: Jobs for you\nContent-Type: text/html; charset=utf-8\n\n<a href='https://ca.indeed.com/viewjob?jk=abc'>Full Stack Developer</a><div>Example Inc - Vancouver, BC</div>"""
        jobs = parse_alert(raw)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Full Stack Developer")
        self.assertEqual(jobs[0]["source"], "Indeed Job Alert")


if __name__ == "__main__":
    unittest.main()

