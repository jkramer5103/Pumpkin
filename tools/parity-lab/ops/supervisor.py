"""Durable two-account task queue; quota pauses resume the exact Codex thread."""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ACCOUNTS, AUTH_ROOT, ROOT, RUNTIME, atomic_json, event_snapshot, fetch_quota, quota_reset, read_json, utc

STATE = RUNTIME / "campaign.json"
QUOTAS = RUNTIME / "quotas.json"


def build_command(account, thread_id=None, output=None):
    command = ["/root/.local/bin/codex", "-a", "never", "-s", "danger-full-access", "exec"]
    if thread_id:
        command += ["resume", thread_id]
    command += ["--ignore-user-config", "--model", "gpt-6.1-sol", "-c", "model_reasoning_effort=high",
                "-c", "features.multi_agent=false", "--json", "-o", str(output), "-"]
    return command


def task_files(account):
    return sorted((ROOT / "ops" / "tasks" / account).glob("*.txt"))


def initial_active(account):
    return subprocess.run(["systemctl", "is-active", "--quiet", f"pumpkin-parity-worker-{account}"],
                          check=False).returncode == 0


def refresh_quotas(previous):
    for account in ACCOUNTS:
        try:
            previous[account] = fetch_quota(account)
        except Exception as error:
            old = previous.get(account, {})
            previous[account] = {**old, "error": type(error).__name__, "attempted_at": utc()}
    atomic_json(QUOTAS, previous)
    return previous


def advance(lane, snapshot):
    lane["completed_tasks"] = lane.get("completed_tasks", 0) + 1
    lane["task_index"] += 1
    lane.update(thread_id=None, retry_at=None, failures=0, adopted=False,
                completed_baseline=snapshot["completed_turns"], status="queued", error=None)


def main():
    RUNTIME.mkdir(exist_ok=True)
    lock = (RUNTIME / "supervisor.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    state = read_json(STATE, {"schema_version": 1, "model": "gpt-6.1-sol", "accounts": {}})
    quotas = read_json(QUOTAS, {})
    for account in ACCOUNTS:
        state["accounts"].setdefault(account, {"task_index": 0, "completed_tasks": 0,
            "completed_baseline": 0, "adopted": True, "status": "starting", "failures": 0,
            "thread_id": None, "retry_at": None})
        # systemd kills owned children on restart; recover their saved conversation.
        lane = state["accounts"][account]
        if lane.get("status") == "working":
            lane["adopted"] = True
    children = {}
    next_quota_check = 0
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        while not stopping:
            now = time.time()
            if now >= next_quota_check:
                quotas = refresh_quotas(quotas)
                next_quota_check = now + 90
            for account, lane in state["accounts"].items():
                files = task_files(account)
                snapshot = event_snapshot(account)
                lane["thread_id"] = snapshot["thread_id"] or lane.get("thread_id")
                lane["activity"] = snapshot
                lane["total_tasks"] = len(files)
                index = lane["task_index"]
                lane["task_title"] = files[index].read_text().splitlines()[0] if index < len(files) else "Campaign complete"
                child = children.get(account)
                external = lane.get("adopted", False) and initial_active(account)
                if external or (child and child.poll() is None):
                    lane["status"] = "working"
                    continue
                if child or lane.get("adopted"):
                    children.pop(account, None)
                    lane["adopted"] = False
                    if snapshot["completed_turns"] > lane.get("completed_baseline", 0) and snapshot["last_error"] is None:
                        advance(lane, snapshot)
                        index = lane["task_index"]
                    else:
                        lane["failures"] = lane.get("failures", 0) + 1
                        lane["error"] = snapshot.get("last_error") or "Worker exited before completing its turn"
                        # Refresh immediately on failure; never guess a 5-hour wait from launch time.
                        try:
                            quotas[account] = fetch_quota(account)
                            atomic_json(QUOTAS, quotas)
                        except Exception:
                            pass
                        reset = quota_reset(quotas.get(account, {}), now)
                        is_limit = any(s in lane["error"].lower() for s in ["usage limit", "rate limit", "quota", "limit reached"])
                        lane["retry_at"] = reset or now + (90 if is_limit else min(300, 30 * lane["failures"]))
                        lane["status"] = "waiting_for_reset" if reset or is_limit else "retrying"
                        if not is_limit and not reset and lane["failures"] >= 3:
                            lane["status"] = "needs_attention"
                if index >= len(files):
                    lane["status"] = "complete"
                    continue
                if lane["status"] == "needs_attention":
                    continue
                reset = quota_reset(quotas.get(account, {}), now)
                if reset:
                    lane.update(status="waiting_for_reset", retry_at=reset)
                    continue
                if lane.get("retry_at") and now < lane["retry_at"]:
                    continue
                # Recheck near the boundary instead of waiting for the normal telemetry poll.
                if lane.get("retry_at"):
                    try:
                        quotas[account] = fetch_quota(account)
                        atomic_json(QUOTAS, quotas)
                        reset = quota_reset(quotas[account], now)
                    except Exception:
                        reset = None
                    if reset:
                        lane.update(status="waiting_for_reset", retry_at=reset)
                        continue
                resuming = bool(lane.get("thread_id"))
                prompt = ("Continue the interrupted task from the current files and conversation. "
                          "The quota reset has been checked. Read AGENTS.md and CONTRACT.md. "
                          "Complete the original task and validate it. Remain on gpt-6.1-sol."
                          if resuming else files[index].read_text())
                output = ROOT / "artifacts" / f"{account}-task-{index:03d}-completion.md"
                environment = dict(os.environ, CODEX_HOME=str(AUTH_ROOT / account))
                for name in ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL", "OPENAI_ORG_ID"):
                    environment.pop(name, None)
                log = (ROOT / "artifacts" / f"{account}-events.jsonl").open("a")
                errors = (ROOT / "artifacts" / f"{account}-stderr.log").open("a")
                lane["completed_baseline"] = snapshot["completed_turns"]
                child = subprocess.Popen(build_command(account, lane.get("thread_id"), output),
                    cwd=ROOT, env=environment, stdin=subprocess.PIPE, stdout=log, stderr=errors,
                    start_new_session=False, text=True)
                child.stdin.write(prompt)
                child.stdin.close()
                log.close()
                errors.close()
                children[account] = child
                lane.update(status="working", started_at=utc(), retry_at=None, pid=child.pid)
            state["updated_at"] = utc()
            atomic_json(STATE, state)
            time.sleep(3)
    finally:
        for child in children.values():
            if child.poll() is None:
                child.terminate()
        state["updated_at"] = utc()
        atomic_json(STATE, state)


if __name__ == "__main__":
    main()
