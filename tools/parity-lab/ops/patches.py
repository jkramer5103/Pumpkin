"""Build an evidence-backed patch ledger from the agents' actual Git commits."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ACCOUNTS, ROOT, RUNTIME, atomic_json, read_json, utc

WORKTREES = Path("/root/pumpkin-parity-worktrees")


def git(path, *arguments):
    return subprocess.run(["git", "-C", str(path), *arguments], capture_output=True,
                          text=True, timeout=20, check=False)


def collect():
    remote = git(WORKTREES / "repo", "ls-remote", "origin",
                 "refs/heads/parity-lab-christine", "refs/heads/parity-lab-jaron")
    if remote.returncode:
        previous = read_json(RUNTIME / "patches.json", {"patches": []})
        previous["remote_verified"] = False
        previous["verification_error"] = "Push verification is temporarily unavailable."
        atomic_json(RUNTIME / "patches.json", previous)
        return previous
    heads = {}
    for line in remote.stdout.splitlines():
        fields = line.split()
        if len(fields) == 2:
            heads[fields[1].rsplit("/", 1)[-1]] = fields[0]
    rows = []
    for account, label in ACCOUNTS.items():
        checkout = WORKTREES / account
        if not checkout.exists():
            continue
        metadata = read_json(ROOT / "artifacts" / f"{account}-fork-status.json", {})
        details = {str(p.get("commit", p.get("head", ""))): p
                   for p in (metadata.get("patches") or []) if isinstance(p, dict)}
        history = git(checkout, "log", "--format=%H%x00%s%x00%ct", "upstream/master..HEAD")
        for line in history.stdout.splitlines():
            fields = line.split("\x00")
            if len(fields) != 3:
                continue
            sha, subject, timestamp = fields
            changed = git(checkout, "diff-tree", "--no-commit-id", "--name-only", "-r", sha).stdout.splitlines()
            source_files = [f for f in changed if f.startswith(("crates/", "assets/", "tools/pumpkin-codegen/")) or f in ("Cargo.toml", "Cargo.lock")]
            if not source_files:
                continue
            branch = f"parity-lab-{account}"
            remote_head = heads.get(branch)
            pushed = bool(remote_head and git(checkout, "merge-base", "--is-ancestor", sha, remote_head).returncode == 0)
            detail = details.get(sha, details.get(sha[:7], {}))
            validation = detail.get("validation")
            if not validation and str(metadata.get("head") or "").startswith(sha[:7]):
                validation = metadata.get("validation")
            if not isinstance(validation, str):
                validation = json.dumps(validation) if validation else "Validation summary not recorded yet."
            title = detail.get("title") or re.sub(r"^[a-z]+(?:\([^)]*\))?!?:\s*", "", subject)
            rows.append({"id": f"{account}:{sha}", "account": label, "branch": branch,
                "commit": sha, "title": title[:250],
                "summary": str(detail.get("summary") or "Changed " + ", ".join(source_files[:3]) + (" and other files." if len(source_files) > 3 else "."))[:700],
                "validation": validation[:1200], "validated": detail.get("validated") is True,
                "pushed": pushed, "timestamp": int(timestamp), "files": source_files,
                "url": f"https://github.com/jkramer5103/Pumpkin/commit/{sha}" if pushed else None})
    rows.sort(key=lambda row: row["timestamp"], reverse=True)
    result = {"updated_at": utc(), "remote_verified": remote.returncode == 0, "patches": rows}
    atomic_json(RUNTIME / "patches.json", result)
    return result


if __name__ == "__main__":
    result = collect()
    print(f"Recorded {len(result['patches'])} source patches.")
