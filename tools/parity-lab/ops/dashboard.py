"""LAN-only, read-only lab dashboard. Never serves credentials or raw worker logs."""
from __future__ import annotations

import argparse
import datetime as dt
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ACCOUNTS, ROOT, RUNTIME, read_json, utc


def catalog():
    rows = []
    for path in sorted((ROOT / "scenarios").glob("*.json")):
        data = read_json(path)
        if not isinstance(data, dict):
            rows.append({"id": path.stem, "title": path.stem, "error": "Invalid scenario JSON"})
            continue
        rows.append({key: data.get(key) for key in
                     ("id", "title", "category", "description", "tags", "notes")}
                    | {"steps": len(data.get("steps", [])), "filename": path.name})
    return rows


def reports():
    paths = list((ROOT / "artifacts" / "runs").glob("*/report.json"))
    return sorted(paths, key=lambda path: path.stat().st_mtime, reverse=True)[:100]


def service_status():
    names = ["pumpkin-parity-supervisor", "pumpkin-parity-vanilla", "pumpkin-parity-pumpkin"]
    try:
        result = subprocess.run(["systemctl", "show", *names, "-p", "Id", "-p", "ActiveState", "-p", "SubState"],
                                capture_output=True, text=True, timeout=4)
        rows = []
        for block in result.stdout.strip().split("\n\n"):
            rows.append(dict(line.split("=", 1) for line in block.splitlines() if "=" in line))
        return rows
    except (OSError, subprocess.TimeoutExpired):
        return []


def status():
    campaign = read_json(RUNTIME / "campaign.json", {})
    quotas = read_json(RUNTIME / "quotas.json", {})
    accounts = []
    for key, label in ACCOUNTS.items():
        lane = campaign.get("accounts", {}).get(key, {})
        fork = read_json(ROOT / "artifacts" / f"{key}-fork-status.json", {})
        concise = {k: lane.get(k) for k in ("status", "task_title", "task_index", "total_tasks", "completed_tasks", "retry_at", "error")}
        accounts.append({"id": key, "label": label, **concise, "quota": quotas.get(key, {}),
                         "fork": {k: fork.get(k) for k in ("branch", "head", "pushed_at", "validation", "findings", "limitations")}})
    routes = read_json(RUNTIME / "account-routing.json", {})
    grouped = {}
    for lane in accounts:
        target = routes.get(lane["id"], lane["id"])
        if target not in grouped:
            grouped[target] = {**lane, "id": target, "label": ACCOUNTS.get(target, target), "worker_count": 1}
        else:
            group = grouped[target]
            group["worker_count"] += 1
            group["completed_tasks"] = (group.get("completed_tasks") or 0) + (lane.get("completed_tasks") or 0)
            group["total_tasks"] = (group.get("total_tasks") or 0) + (lane.get("total_tasks") or 0)
            if lane.get("status") == "working": group["status"] = "working"
    accounts = list(grouped.values())
    for group in accounts:
        if group["worker_count"] > 1: group["task_title"] = "{} workers sharing this subscription".format(group["worker_count"])
    run_paths = reports()
    latest_report = read_json(run_paths[0], {}) if run_paths else {}
    latest = {k: latest_report.get(k) for k in ("run_id", "summary", "confirmed_mismatch_count", "complete")} if latest_report else None
    usage = shutil.disk_usage(ROOT)
    return {"updated_at": utc(), "campaign_updated_at": campaign.get("updated_at"),
            "model": "gpt-6.1-sol", "accounts": accounts,
            "scenario_count": len(catalog()), "run_count": len(run_paths),
            "latest": latest, "services": service_status(),
            "disk_free_gb": round(usage.free / 1024 ** 3, 1),
            "versions": read_json(RUNTIME / "manifest.json", {}),
            "published": read_json(RUNTIME / "published.json", {}),
            "patch_ledger": read_json(RUNTIME / "patches.json", {"patches": []}),
            "policy": {"network": "LAN only", "auto_resume": True, "banked_resets": "manual",
                       "paid_overage": False, "scope": "Command-observable server behavior"}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, body, content_type="application/json", code=200):
        data = json.dumps(body).encode() if content_type == "application/json" else body
        self.send_response(code)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/status":
            return self.respond(status())
        if path == "/api/scenarios":
            return self.respond(catalog())
        if path == "/api/runs":
            rows = []
            for report_path in reports():
                data = read_json(report_path, {})
                rows.append({"directory": report_path.parent.name, **{key: data.get(key) for key in
                    ("run_id", "started_at", "finished_at", "summary", "minecraft_version")}})
            return self.respond(rows)
        if path.startswith("/api/runs/"):
            name = path.removeprefix("/api/runs/")
            if not re.fullmatch(r"[A-Za-z0-9_.-]{1,150}", name) or name in (".", ".."):
                return self.respond({"error": "Invalid run"}, code=400)
            report = read_json(ROOT / "artifacts" / "runs" / name / "report.json")
            return self.respond(report or {"error": "Run not found"}, code=200 if report else 404)
        assets = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}
        if path in assets:
            file = ROOT / "web" / assets[path]
            return self.respond(file.read_bytes(), mimetypes.guess_type(file.name)[0] or "text/plain")
        return self.respond({"error": "Not found"}, code=404)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.2.223")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    print(f"Pumpkin Parity Lab: http://{args.host}:{args.port}", flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
