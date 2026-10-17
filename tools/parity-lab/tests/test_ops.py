import importlib.util
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ops"))
import supervisor
from common import quota_reset
from supervisor import build_command, advance, is_provider_safety_rejection, skip_blocked_task, replenish_source_tasks


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


class SafetyRejectionRecoveryTests(unittest.TestCase):
    def test_explicit_provider_rejection_is_skippable(self):
        self.assertTrue(is_provider_safety_rejection({"message":
            "This content was flagged for possible cybersecurity risk."}))

    def test_other_errors_are_not_skippable(self):
        for error in (None, "Usage limit reached", "Connection timed out",
                      "Worker exited before completing its turn", "Account routing mismatch"):
            with self.subTest(error=error):
                self.assertFalse(is_provider_safety_rejection(error))

    def test_skip_preserves_evidence_without_counting_success(self):
        lane = {"task_index": 4, "task_title": "Blocked job", "thread_id": "refused",
                "completed_tasks": 4, "failures": 1, "retry_at": 123}
        skip_blocked_task(lane, {"last_error": "safety_violation", "completed_turns": 8})
        self.assertEqual(lane["task_index"], 5)
        self.assertEqual(lane["completed_tasks"], 4)
        self.assertEqual(lane["blocked_tasks"][0]["thread_id"], "refused")
        self.assertEqual(lane["blocked_tasks"][0]["error"], "safety_violation")
        self.assertEqual(lane["ignored_thread_id"], "refused")
        self.assertIsNone(lane["thread_id"])
        self.assertIsNone(lane["retry_at"])
        self.assertEqual(lane["status"], "queued")
        self.assertEqual(lane["completed_baseline"], 8)

    def test_last_task_skip_exhausts_queue_and_keeps_prior_blocks(self):
        lane = {"task_index": 7, "thread_id": "last", "blocked_tasks": [{"task_index": 4}]}
        skip_blocked_task(lane, {"last_error": "safety_violation", "completed_turns": 8})
        self.assertEqual(lane["task_index"], 8)
        self.assertEqual(len(lane["blocked_tasks"]), 2)


class ContinuousSourceCampaignTests(unittest.TestCase):
    def test_empty_queue_generates_one_assignment_without_resuming_old_thread(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "ops/source-tasks").mkdir(parents=True)
            (root / "ops/tasks/christine").mkdir(parents=True)
            (root / "runtime").mkdir()
            (root / "runtime/source-campaign.json").write_text('{"enabled_accounts":["christine"]}')
            (root / "ops/source-tasks/christine.txt").write_text("Fix another Pumpkin source defect\n")
            lane = {"task_index": 0, "thread_id": "finished", "status": "complete"}
            with patch.object(supervisor, "ROOT", root), patch.object(supervisor, "RUNTIME", root / "runtime"):
                files = replenish_source_tasks("christine", lane, [])
                self.assertEqual(len(files), 1)
                self.assertEqual(lane["status"], "queued")
                self.assertIsNone(lane["thread_id"])
                self.assertEqual(lane["ignored_thread_id"], "finished")
                self.assertEqual(replenish_source_tasks("christine", lane, files), files)
                advance(lane, {"completed_turns": 1, "thread_id": "newly-finished"})
                files = replenish_source_tasks("christine", lane, files)
                self.assertEqual(len(files), 2)
                self.assertEqual(lane["ignored_thread_id"], "newly-finished")
                self.assertEqual(lane["completed_tasks"], 1)

    def test_finite_campaign_is_unchanged_without_opt_in(self):
        with patch.object(supervisor, "read_json", return_value={}):
            lane = {"task_index": 8, "status": "complete"}
            self.assertEqual(replenish_source_tasks("christine", lane, []), [])
            self.assertEqual(lane["status"], "complete")


class StaleQuotaWaitTests(unittest.TestCase):
    def test_usable_quota_releases_old_weekly_deadline(self):
        lane = {"status": "waiting_for_reset", "retry_at": 500000, "error": None}
        quota = {"checked_at": "fresh", "allowed": True, "limit_reached": False,
                 "five_hour": {"used_percent": 0}, "weekly": {"used_percent": 0}}
        supervisor.release_stale_quota_wait(lane, quota, 100)
        self.assertEqual(lane["status"], "queued")
        self.assertIsNone(lane["retry_at"])

    def test_unconfirmed_or_exhausted_telemetry_does_not_release_wait(self):
        for quota in ({"allowed": True, "limit_reached": False},
                      {"checked_at": "old", "allowed": True, "limit_reached": False, "error": "TimeoutError"},
                      {"checked_at": "fresh", "allowed": True, "limit_reached": False,
                       "weekly": {"used_percent": 100, "reset_at": 500000}}):
            with self.subTest(quota=quota):
                lane = {"status": "waiting_for_reset", "retry_at": 500000}
                supervisor.release_stale_quota_wait(lane, quota, 100)
                self.assertEqual(lane["retry_at"], 500000)

    def test_provider_error_retains_short_backoff(self):
        lane = {"status": "waiting_for_reset", "retry_at": 500000, "error": "Usage limit reached"}
        quota = {"checked_at": "fresh", "allowed": True, "limit_reached": False}
        supervisor.release_stale_quota_wait(lane, quota, 100)
        self.assertEqual(lane["status"], "retrying")
        self.assertEqual(lane["retry_at"], 190)

    def test_regular_failure_backoff_is_unchanged(self):
        lane = {"status": "retrying", "retry_at": 200}
        supervisor.release_stale_quota_wait(lane, {"checked_at": "fresh", "allowed": True,
                                                  "limit_reached": False}, 100)
        self.assertEqual(lane["retry_at"], 200)


if __name__ == "__main__":
    unittest.main()
