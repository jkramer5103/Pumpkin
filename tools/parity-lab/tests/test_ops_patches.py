import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ops"))
import patches


class PatchLedgerIntegrationTests(unittest.TestCase):
    def test_tracks_real_source_commits_and_checks_pushes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            remote = base / "remote.git"
            trees = base / "trees"
            repo = trees / "repo"
            repo.mkdir(parents=True)
            lab = base / "lab"
            (lab / "artifacts").mkdir(parents=True)
            (lab / "runtime").mkdir()

            def git(path, *args):
                result = subprocess.run(["git", "-C", str(path), *args],
                                        capture_output=True, text=True, check=True)
                return result.stdout.strip()

            subprocess.run(["git", "init", "--bare", str(remote)], capture_output=True, check=True)
            git(repo, "init", "-b", "master")
            git(repo, "config", "user.name", "Ledger test")
            git(repo, "config", "user.email", "ledger@example.invalid")
            (repo / "README.md").write_text("baseline")
            git(repo, "add", ".")
            git(repo, "commit", "-m", "baseline")
            baseline = git(repo, "rev-parse", "HEAD")
            git(repo, "update-ref", "refs/remotes/upstream/master", baseline)
            git(repo, "remote", "add", "origin", str(remote))
            checkout = trees / "christine"
            git(repo, "worktree", "add", "-b", "parity-lab-christine", str(checkout), "HEAD")
            (checkout / "README.md").write_text("documentation only")
            git(checkout, "add", ".")
            git(checkout, "commit", "-m", "docs: clarify baseline")
            with patch.multiple(patches, ROOT=lab, RUNTIME=lab / "runtime", WORKTREES=trees):
                self.assertEqual(patches.collect()["patches"], [])
                source = checkout / "crates" / "example" / "src"
                source.mkdir(parents=True)
                (source / "lib.rs").write_text("pub fn fixed() {}\n")
                git(checkout, "add", ".")
                git(checkout, "commit", "-m", "fix(command): preserve score on failure")
                sha = git(checkout, "rev-parse", "HEAD")
                local = patches.collect()["patches"]
                self.assertEqual(len(local), 1)
                self.assertFalse(local[0]["pushed"])
                self.assertEqual(local[0]["commit"], sha)
                git(checkout, "push", "origin", "HEAD:refs/heads/parity-lab-christine")
                metadata = {"head": sha, "patches": [{"commit": sha,
                    "summary": "Failed operations retain the original score.",
                    "validation": "Regression test passed.", "validated": True}]}
                (lab / "artifacts" / "christine-fork-status.json").write_text(json.dumps(metadata))
                pushed = patches.collect()["patches"][0]
                self.assertTrue(pushed["pushed"])
                self.assertTrue(pushed["validated"])
                self.assertEqual(pushed["summary"], metadata["patches"][0]["summary"])
                self.assertIn(sha, pushed["url"])


if __name__ == "__main__":
    unittest.main()
