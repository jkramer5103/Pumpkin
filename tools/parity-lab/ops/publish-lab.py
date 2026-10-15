"""Snapshot original lab sources into the authorized fork's campaign branch."""
from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPO = Path("/root/pumpkin-parity-worktrees/repo")
EXCLUDE = {".git", "runtime", "artifacts", ".venv", "__pycache__", "node_modules", ".pytest_cache"}


def git(*arguments, capture=False):
    return subprocess.run(["git", "-C", str(REPO), *arguments], check=True,
                          text=True, capture_output=capture)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", default="feat(parity): add autonomous Minecraft differential testing lab")
    args = parser.parse_args()
    lock = Path("/root/pumpkin-parity-worktrees/publish.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX)
    branch = git("branch", "--show-current", capture=True).stdout.strip()
    if branch != "parity-lab":
        raise SystemExit("Refusing to publish outside parity-lab branch")
    origin = git("remote", "get-url", "--push", "origin", capture=True).stdout.strip()
    if origin != "https://github.com/jkramer5103/Pumpkin.git":
        raise SystemExit("Unexpected fork destination")
    # Reject a transient partial edit rather than publishing it while another lane writes.
    check = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
                           cwd=ROOT, capture_output=True, text=True)
    if check.returncode:
        raise SystemExit("Lab verification failed; publication deferred. " + check.stderr[-1800:])
    sources = []
    for file in ROOT.rglob("*"):
        relative = file.relative_to(ROOT)
        if not file.is_file() or any(part in EXCLUDE or part.endswith(".egg-info") for part in relative.parts):
            continue
        if file.suffix in (".pyc", ".bin", ".jar", ".sqlite", ".log"):
            continue
        data = file.read_bytes()
        if re.search(rb"(?:sk-(?:proj-|live-)?[A-Za-z0-9_-]{24,}|gh[opusr]_[A-Za-z0-9]{25,}|-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----)", data):
            raise SystemExit(f"Possible credential detected in {relative}; refusing to publish")
        sources.append((relative, data))
    destination = REPO / "tools" / "parity-lab"
    destination.mkdir(parents=True, exist_ok=True)
    present = {str(relative) for relative, _ in sources}
    tracked = git("ls-files", "--", "tools/parity-lab", capture=True).stdout.splitlines()
    for entry in tracked:
        relative = str(Path(entry).relative_to("tools/parity-lab"))
        if relative not in present:
            (REPO / entry).unlink(missing_ok=True)
    for relative, data in sources:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod((ROOT / relative).stat().st_mode & 0o777)
    git("add", "--", "tools/parity-lab")
    diff = subprocess.run(["git", "-C", str(REPO), "diff", "--cached", "--quiet"], check=False)
    if diff.returncode == 1:
        git("commit", "-m", args.message)
    elif diff.returncode:
        raise SystemExit("Could not inspect staged changes")
    git("push", "origin", "HEAD:refs/heads/parity-lab")
    head = git("rev-parse", "HEAD", capture=True).stdout.strip()
    sys.path.insert(0, str(ROOT / "ops"))
    from common import atomic_json, utc
    atomic_json(ROOT / "runtime" / "published.json", {"branch": "parity-lab", "head": head,
        "pushed_at": utc(),
        "unit_tests_passed": int(re.search(r"Ran (\d+) tests?", check.stderr).group(1)) if re.search(r"Ran (\d+) tests?", check.stderr) else None,
        "url": "https://github.com/jkramer5103/Pumpkin/tree/parity-lab/tools/parity-lab"})
    print("Published parity-lab at " + head)


if __name__ == "__main__":
    main()
