# Pumpkin Parity Lab

An unattended differential-testing lab for Minecraft Java 26.3 and Pumpkin.
The live deployment is on `ssh codex`, in `/root/pumpkin-parity-lab`.

**LAN dashboard:** <http://192.168.2.223:8787>

The dashboard is read-only and binds to the server's LAN address. It shows
per-subscription quota, reset countdowns, and a concise summary of actual Pumpkin
patches with validation and commit links. Pushes are cross-checked against Git;
the interface does not stream commands or count findings as fixes. Neither server nor RCON
listens outside loopback. No public hosting or tunnel is configured by this lab.

## What it actually tests

Initial coverage is command-observable server behavior: blocks, state predicates,
fills/clones, scoreboards, selectors and entities. The first catalog has 37 cases.
Reference scenarios are checked against real vanilla, not assumed from source.
The released Pumpkin binary has known command/capability and unloaded-world gaps;
these are visible and are not automatically called confirmed gameplay defects.
Connected-client gameplay, movement, visuals and combat require separate work.

Each run saves the exact scenario, raw responses, expectations and a JSON report
under `artifacts/runs/`. Repeat trials identify flakiness. Both servers must satisfy
positive expectations: two equal empty/error responses cannot pass. The engine
uses a shared process lock to serialize arena mutations. The reducer must rerun
candidates before claiming a minimized reproducer.

## Autonomous workers

Two isolated native ChatGPT logins are configured outside the source tree:
Christine and Jaron. Both use exactly `gpt-6.1-sol`, with `danger-full-access` and
approval policy `never`. They do not use Joon, paid API fallback, or automatic
banked-reset redemption. Existing global Codex configuration is ignored.

The campaign currently contains eight substantial tasks per account (16 total).
It covers the engine, real-server integration, reduction, repeated trials,
bounded seeded fuzzing, client feasibility, broad scenario coverage, source fixes,
and validation. It stops when the finite queue is done rather than manufacturing
endless tasks. Queue files live under `ops/tasks/`.

On quota exhaustion, the supervisor reads that subscription's actual reset time,
waits, and resumes the exact interrupted Codex thread. Exhausted weekly limits
also delay work; resetting only the 5-hour window cannot bypass a weekly limit.
The queue and thread identities persist in `runtime/campaign.json`, and systemd
starts the supervisor again after reboot. Non-quota failures retry a bounded
number of times before becoming visible as needing attention.

The user authorizes autonomous source fixes and pushes to
<https://github.com/jkramer5103/Pumpkin>. See `ops/FORK.md` for worktrees, branches,
build resource limits and validation requirements. No upstream PRs are opened.

## Operate on the server

```bash
cd /root/pumpkin-parity-lab
python3 -m unittest discover -s tests -v
python3 -m lab list
python3 -m lab run --targets runtime/targets.json --scenarios scenarios \
  --output artifacts/runs --repeat 2
systemctl status pumpkin-parity-supervisor pumpkin-parity-dashboard
journalctl -u pumpkin-parity-supervisor -f
```

Stop or resume autonomous inference:

```bash
systemctl stop pumpkin-parity-supervisor
systemctl start pumpkin-parity-supervisor
```

During initial construction two transient bootstrap workers also run as
`pumpkin-parity-worker-christine` and `pumpkin-parity-worker-jaron`. Stop those
too if they are still active and you want to stop all work immediately. Later
jobs are owned directly by the supervisor.

The test servers are `pumpkin-parity-vanilla` and `pumpkin-parity-pumpkin`.
Provisioning and standalone RCON checks are documented in `docs/servers.md`.
Credentials, target passwords, world data, logs, and decompiled/downloaded
third-party artifacts are excluded from Git and must remain excluded.
