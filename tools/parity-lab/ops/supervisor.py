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


def replenish_source_tasks(account, lane, files):
    """Create one bounded source assignment at a time for opted-in campaigns."""
    config = read_json(RUNTIME / "source-campaign.json", {})
    if account not in config.get("enabled_accounts", []) or lane["task_index"] < len(files):
        return files
    template = ROOT / "ops" / "source-tasks" / f"{account}.txt"
    if not template.is_file():
        raise RuntimeError(f"Missing source campaign template for {account}")
    index = lane["task_index"]
    path = ROOT / "ops" / "tasks" / account / f"{index:03d}-source.txt"
    path.write_text(template.read_text() + f"\nSource assignment sequence: {index}.\n")
    lane.update(status="queued", thread_id=None, retry_at=None, error=None,
                ignored_thread_id=lane.get("thread_id") or lane.get("ignored_thread_id"))
    return task_files(account)


def initial_active(account):
    return subprocess.run(["systemctl", "is-active", "--quiet", f"pumpkin-parity-worker-{account}"],
                          check=False).returncode == 0


def dependency_active(unit):
    return subprocess.run(["systemctl", "is-active", "--quiet", unit], check=False).returncode == 0


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
    lane["ignored_thread_id"] = snapshot.get("thread_id") or lane.get("thread_id")
    lane.update(thread_id=None, retry_at=None, failures=0, adopted=False,
                completed_baseline=snapshot["completed_turns"], status="queued", error=None)


def is_provider_safety_rejection(error):
    """Match explicit provider refusals, not ordinary worker or quota errors."""
    message = str(error or "").lower()
    return any(marker in message for marker in (
        "this content was flagged for possible cybersecurity risk",
        "content_policy_violation", "safety_violation",
    ))


def skip_blocked_task(lane, snapshot):
    """Keep refusal evidence and start the next assignment in a fresh thread."""
    lane.setdefault("blocked_tasks", []).append({
        "task_index": lane["task_index"], "task_title": lane.get("task_title"),
        "thread_id": lane.get("thread_id"), "error": snapshot["last_error"],
        "recorded_at": utc(), "reason": "Provider safety rejection; task skipped without retry",
    })
    lane["ignored_thread_id"] = lane.get("thread_id")
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
                files = replenish_source_tasks(account, lane, task_files(account))
                snapshot = event_snapshot(account)
                if snapshot["thread_id"] != lane.get("ignored_thread_id"):
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
                    wait_path = RUNTIME / "worker-waits" / f"{account}.json"
                    wait = read_json(wait_path, {})
                    unit = wait.get("unit", "")
                    if unit.startswith("pumpkin-parity-") and unit.endswith(".scope"):
                        lane.update(status="waiting_for_build", waiting_for=unit,
                                    completed_baseline=snapshot["completed_turns"], retry_at=None)
                        continue
                    if is_provider_safety_rejection(snapshot.get("last_error")):
                        # Never retry or rephrase a refused task. Other assignments may proceed.
                        skip_blocked_task(lane, snapshot)
                        index = lane["task_index"]
                        atomic_json(STATE, state)
                    elif snapshot["completed_turns"] > lane.get("completed_baseline", 0) and snapshot["last_error"] is None:
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
                files = replenish_source_tasks(account, lane, files)
                lane["total_tasks"] = len(files)
                lane["task_title"] = files[index].read_text().splitlines()[0] if index < len(files) else "Campaign complete"
                if index >= len(files):
                    lane["status"] = "complete"
                    continue
                if lane.get("waiting_for"):
                    if dependency_active(lane["waiting_for"]):
                        lane["status"] = "waiting_for_build"
                        continue
                    (RUNTIME / "worker-waits" / f"{account}.json").unlink(missing_ok=True)
                    lane.update(waiting_for=None, status="queued", retry_at=None)
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
                          "Read ops/FORK.md: the user has additionally authorized autonomous "
                          "Pumpkin source fixes and pushes to jkramer5103/Pumpkin in YOLO mode. "
                          "GitHub authentication has been repaired: repository-local credentials "
                          "and GH_CONFIG_DIR are configured. Recheck pushes instead of asking for login. "
                          "If a build or test scope blocks further useful work, run "
                          "python3 ops/wait-for-build.py --account " + account +
                          " --unit THE_SCOPE --reason 'short reason', then end your turn. "
                          "The supervisor waits without inference and resumes this exact thread "
                          "when the scope exits; inspect its actual result then. Do not repeatedly "
                          "poll build logs with model turns. Complete the current task and validate it. "
                          "Remain on gpt-6.1-sol.\nCurrent queue assignment:\n" + files[index].read_text()
                          if resuming else files[index].read_text())
                routes = read_json(RUNTIME / "account-routing.json", {})
                route = routes.get(account, account)
                expected = read_json(AUTH_ROOT / route / "auth.json", {}).get("tokens", {}).get("account_id") if route in ACCOUNTS else None
                actual = read_json(AUTH_ROOT / account / "auth.json", {}).get("tokens", {}).get("account_id")
                if not expected or actual != expected:
                    lane.update(status="needs_attention", error="Account routing mismatch; inference blocked")
                    continue
                output = ROOT / "artifacts" / f"{account}-task-{index:03d}-completion.md"
                environment = dict(os.environ, CODEX_HOME=str(AUTH_ROOT / account),
                                   GH_CONFIG_DIR="/root/.config/gh")
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
