from __future__ import annotations

import unittest
from pathlib import Path


class TheInformationWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = (
            Path(__file__).resolve().parents[1]
            / ".github"
            / "workflows"
            / "daily-news.yml"
        ).read_text(encoding="utf-8")

    def test_normal_daily_crawl_does_not_exclude_the_information(self):
        self.assertNotIn('args+=(--exclude-source "the information")', self.workflow)

    def test_any_non_authenticated_result_triggers_alternate_runner(self):
        self.assertIn('crawl_mode == "rss_authenticated"', self.workflow)
        self.assertIn('status in {"healthy", "idle"}', self.workflow)
        self.assertIn("retry = True", self.workflow)

    def test_alternate_runner_failure_is_reported_without_failing_daily_run(self):
        self.assertIn("continue-on-error: true", self.workflow)
        self.assertIn("Report failed full-text recovery", self.workflow)
        self.assertIn("online_recovery_failed", self.workflow)
        self.assertIn("Other channels remain unaffected", self.workflow)


if __name__ == "__main__":
    unittest.main()
