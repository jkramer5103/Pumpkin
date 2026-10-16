"""Finalize abandoned evidence without executing or retrying server commands."""
import json
import os
from pathlib import Path

from .runner import _update_summary, atomic_json, process_lock, utc_now
from .schema import SchemaError, read_json


def process_identity(pid=None):
    """Identify a Linux process across PID reuse and host reboots."""
    pid = os.getpid() if pid is None else pid
    return {'pid': pid, 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'start_ticks': Path(f'/proc/{pid}/stat').read_text().rpartition(')')[2].split()[19]}


def recover_run(directory, *, lock_timeout=30.0, lock_path=None):
    directory = Path(directory).resolve()
    # Re-read only after the active runner has released the same engine lock.
    with process_lock(lock_path, lock_timeout):
        report = read_json(directory / 'report.json')
        if (report.get('schema_version') != 1 or report.get('run_id') != directory.name
                or not isinstance(report.get('results'), list)):
            raise SchemaError('Not an engine run report')
        if report.get('state') != 'running':
            capabilities = [c['status'] for c in report.get('timing_capabilities', {}).values()]
            code = (2 if not report.get('complete') or report['summary']['error'] or 'error' in capabilities else
                    1 if report['summary']['different'] or 'unsupported' in capabilities else 0)
            return directory, report, code
        owner = report.get('owner')
        if not isinstance(owner, dict) or type(owner.get('pid')) is not int or owner['pid'] <= 0:
            raise SchemaError('Run has no process identity; safe automatic recovery is unavailable')
        try:
            active = process_identity(owner['pid']) == owner
        except FileNotFoundError:
            active = False
        if active:
            raise SchemaError('Run owner is still alive, possibly waiting for the engine lock')
        pending = {}
        transcript_issues = []
        for name in ('vanilla', 'pumpkin'):
            path = directory / 'transcripts' / (name + '.jsonl')
            if not path.exists():
                transcript_issues.append({'target': name, 'issue': 'Transcript absent'})
                continue
            # Preserve truncated/corrupt lines verbatim in the original file.
            with path.open(encoding='utf-8', errors='replace') as handle:
                for line_number, line in enumerate(handle, 1):
                    try:
                        event = json.loads(line)
                        if not isinstance(event, dict):
                            raise ValueError('Expected event object')
                        key = (name, event.get('scenario_id'), event.get('repeat'),
                               event.get('phase'), event.get('index'))
                        if event.get('event') == 'request':
                            pending[key] = event
                        elif event.get('event') == 'response':
                            pending.pop(key, None)
                    except (ValueError, TypeError):
                        transcript_issues.append({'target': name, 'line': line_number,
                                                  'issue': 'Unreadable transcript event'})
        for result in report['results']:
            attempts = result['attempts']
            if len(attempts) != report['repeat'] or any('status' not in a for a in attempts):
                result.update(status='error', reason='Abandoned before all trials completed',
                              confirmed_mismatch=False)
                if 'trial_details' in result:
                    result['trial_details'].update(series_complete=False, classification='incomplete')
        for capability in report.get('timing_capabilities', {}).values():
            if capability['status'] == 'testing':
                capability.update(status='error', reason='Abandoned timing probe')
        report.update(state='abandoned', complete=False, finished_at=utc_now(),
                      error={'kind': 'AbandonedRun', 'reason': 'Recovered after the engine lock became available'},
                      recovery={'recovered_at': utc_now(), 'commands_replayed': False,
                                'uncertain_requests': list(pending.values()),
                                'transcript_issues': transcript_issues,
                                'world_state': 'Unknown: cleanup and tick restoration are not proven; inspect raw evidence before another comparison'})
        _update_summary(report)
        atomic_json(directory / 'report.json', report)
        return directory, report, 2
