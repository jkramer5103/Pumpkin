import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ops"))
from common import quota_reset
from supervisor import build_command, advance


class QuotaRecoveryTests(unittest.TestCase):
    def test_waits_for_both_exhausted_windows(self):
        quota = {"allowed": False,
                 "five_hour": {"used_percent": 100, "reset_at": 200},
                 "weekly": {"used_percent": 100, "reset_at": 500}}
        self.assertEqual(quota_reset(quota, 100), 515)

    def test_does_not_wait_for_weekly_window_with_capacity(self):
        quota = {"five_hour": {"used_percent": 100, "reset_at": 200},
                 "weekly": {"used_percent": 10, "reset_at": 500}}
        self.assertEqual(quota_reset(quota, 100), 215)

    def test_usable_quota_does_not_pause(self):
        self.assertIsNone(quota_reset({"allowed": True, "five_hour": {"used_percent": 2}}, 100))

    def test_unknown_block_rechecks_instead_of_guessing_five_hours(self):
        self.assertEqual(quota_reset({"allowed": False}, 100), 190)

    def test_resume_keeps_exact_thread_and_exact_model(self):
        command = build_command("christine", "known-session", "/tmp/result.md")
        self.assertEqual(command[command.index("resume") + 1], "known-session")
        self.assertEqual(command[command.index("--model") + 1], "gpt-6.1-sol")
        self.assertIn("--ignore-user-config", command)
        self.assertNotIn("--last", command)

    def test_completed_job_does_not_resume_previous_thread(self):
        lane = {"task_index": 0, "thread_id": "old", "failures": 1}
        advance(lane, {"completed_turns": 1})
        self.assertEqual(lane["task_index"], 1)
        self.assertIsNone(lane["thread_id"])
        self.assertEqual(lane["completed_baseline"], 1)


if __name__ == "__main__":
    unittest.main()
