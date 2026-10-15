"""Read-only telemetry for the two explicitly authorized subscriptions."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
ACCOUNTS = {"christine": "Christine", "jaron": "Jaron"}
AUTH_ROOT = Path("/root/.config/pumpkin-parity-lab/accounts")


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2))
    tmp.chmod(0o600)
    os.replace(tmp, path)


def fetch_quota(account):
    if account not in ACCOUNTS:
        raise ValueError("Unknown account")
    auth = read_json(AUTH_ROOT / account / "auth.json")
    tokens = auth["tokens"]
    request = urllib.request.Request(
        "https://chatgpt.com/backend-api/wham/usage",
        headers={"Authorization": "Bearer " + tokens["access_token"],
                 "Chatgpt-Account-Id": tokens["account_id"],
                 "User-Agent": "codex-cli/0.162.1"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)
    rate = data.get("rate_limit") or {}
    return {"checked_at": utc(), "plan": data.get("plan_type"),
            "allowed": rate.get("allowed"),
            "limit_reached": rate.get("limit_reached"),
            "five_hour": rate.get("primary_window"),
            "weekly": rate.get("secondary_window"),
            "banked_count": (data.get("rate_limit_reset_credits") or {}).get("available_count"),
            "error": None}


def quota_reset(quota, now=None):
    """A worker can run only after every currently exhausted window resets."""
    now = time.time() if now is None else now
    resets = []
    for name in ("five_hour", "weekly"):
        window = quota.get(name) or {}
        if window.get("used_percent", 0) >= 100:
            stamp = window.get("reset_at")
            if isinstance(stamp, (int, float)) and stamp > now:
                resets.append(stamp)
    if resets:
        return max(resets) + 15
    if quota.get("allowed") is False or quota.get("limit_reached"):
        return now + 90
    return None


def event_snapshot(account):
    path = ROOT / "artifacts" / f"{account}-events.jsonl"
    result = {"thread_id": None, "completed_turns": 0, "failed_turns": 0,
              "events": [], "last_error": None, "last_event_type": None,
              "updated_at": None, "usage": {}}
    if not path.exists():
        return result
    result["updated_at"] = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat()
    # Files stay local. Only deliberately selected fields ever reach the dashboard.
    with path.open() as handle:
        for line in handle:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            kind = event.get("type")
            result["last_event_type"] = kind
            if kind == "thread.started":
                result["thread_id"] = event.get("thread_id")
            elif kind == "turn.completed":
                result["completed_turns"] += 1
                result["last_error"] = None
                result["usage"] = event.get("usage", {})
            elif kind in ("error", "turn.failed"):
                if kind == "turn.failed":
                    result["failed_turns"] += 1
                error = event.get("error", event.get("message", "Worker error"))
                result["last_error"] = str(error)[:900]
            item = event.get("item") or {}
            if kind == "item.completed" and item.get("type") == "agent_message":
                result["events"].append({"kind": "message", "text": item.get("text", "")[:2400]})
            elif kind == "item.started" and item.get("type") == "command_execution":
                result["events"].append({"kind": "command", "text": item.get("command", "")[:240]})
            result["events"] = result["events"][-16:]
    return result
