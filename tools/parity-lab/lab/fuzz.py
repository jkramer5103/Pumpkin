"""Finite seeded state-machine comparisons. No user-provided command templates."""
from __future__ import annotations

from contextlib import contextmanager
import random
import signal
import shlex
import sys
import tempfile
import time
from pathlib import Path

from .runner import atomic_json, run, utc_now
from .schema import load_targets, validate_scenario
from .shrink import _console_version, failure_identity, load_versions, shrink_scenario

OBJECTIVE = 'pp_fuzz'
ARENA = '0 80 0 3 80 3'
BLOCKS = ('stone', 'dirt', 'glass', 'gold_block')


@contextmanager
def time_budget(seconds):
    """One campaign deadline, including reducer probes; cleanup still runs.

    POSIX main-thread CLI only. Refuse to replace another owner's alarm.
    The one-shot alarm never interrupts cleanup a second time.
    """
    if signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
        raise ValueError('fuzz cannot replace an active process timer')
    previous = signal.getsignal(signal.SIGALRM)
    def expired(signum, frame):
        raise TimeoutError('Fuzz campaign time budget exhausted')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def generate(seed, actions=12, mode='mixed'):
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError('seed must be an unsigned 64-bit integer')
    if type(actions) is not int or not 4 <= actions <= 40:
        raise ValueError('actions must be between 4 and 40')
    if mode not in ('mixed', 'scoreboard', 'blocks'):
        raise ValueError('unknown fuzz mode')
    rng = random.Random(seed)
    steps, generated = [], []
    scores = {'#a': rng.randint(-32, 32), '#b': rng.choice((-7, -3, -1, 1, 3, 7))}
    cells = {(x, z): 'air' for x in range(4) for z in range(4)}
    def emit(command, expected=None):
        steps.append({'command': command, **({'observe': True, 'expect_contains': expected} if expected else {})})
    setup = [f'scoreboard objectives add {OBJECTIVE} dummy']
    setup += [f'scoreboard players set {holder} {OBJECTIVE} {value}' for holder, value in scores.items()]
    # Two distinct fills establish a known state without an expected no-op error.
    # Inert blocks only; no fluids, falling blocks, entities or drops.
    if mode != 'scoreboard':
        setup += [f'fill {ARENA} minecraft:barrier replace', f'fill {ARENA} minecraft:air replace']
    for index in range(actions):
        kind = mode if mode != 'mixed' else ('scoreboard' if index % 2 == 0 else 'blocks')
        before = len(steps)
        if kind == 'scoreboard':
            op = rng.choice(('add', 'remove', '+=', '-=', '*=', '/=', '%=', '=', '<', '>', '><'))
            if op in ('add', 'remove'):
                value = rng.randint(1, 19)
                emit(f'scoreboard players {op} #a {OBJECTIVE} {value}')
                scores['#a'] += value if op == 'add' else -value
            else:
                # Never divide by zero; bound intermediates far below i32 overflow.
                if scores['#b'] == 0 or abs(scores['#a']) > 10000 or abs(scores['#b']) > 100:
                    scores['#b'] = rng.choice((-7, -3, -1, 1, 3, 7))
                    emit(f'scoreboard players set #b {OBJECTIVE} {scores["#b"]}')
                emit(f'scoreboard players operation #a {OBJECTIVE} {op} #b {OBJECTIVE}')
                a, b = scores['#a'], scores['#b']
                if op == '><': scores['#a'], scores['#b'] = b, a
                else:
                    scores['#a'] = {'+=': lambda: a+b, '-=': lambda: a-b, '*=': lambda: a*b,
                        '/=': lambda: a//b, '%=': lambda: a%b, '=': lambda: b,
                        '<': lambda: min(a,b), '>': lambda: max(a,b)}[op]()
            for holder, value in scores.items():
                emit(f'execute if score {holder} {OBJECTIVE} matches {value}', 'Test passed')
        else:
            x, z = rng.randrange(4), rng.randrange(4)
            end_x = min(3, x + rng.randrange(2))
            end_z = min(3, z + rng.randrange(2))
            old = {cells[(x, z)]}
            block = rng.choice([b for b in BLOCKS if b not in old])
            if (x, z) == (end_x, end_z):
                emit(f'setblock {x} 80 {z} minecraft:{block}')
            else:
                emit(f'fill {x} 80 {z} {end_x} 80 {end_z} minecraft:{block} replace')
            for xx in range(x, end_x+1):
                for zz in range(z, end_z+1):
                    cells[(xx, zz)] = block
            # Check the whole arena, including cells that should remain untouched.
            for (xx, zz), expected in cells.items():
                emit(f'scoreboard players set #probe {OBJECTIVE} 0')
                emit(f'execute if block {xx} 80 {zz} minecraft:{expected} run scoreboard players set #probe {OBJECTIVE} 1')
                emit(f'execute if score #probe {OBJECTIVE} matches 1', 'Test passed')
        generated.append({'index': index, 'kind': kind, 'steps': steps[before:]})
    cleanup = [f'scoreboard objectives remove {OBJECTIVE}']
    if mode != 'scoreboard':
        cleanup += [f'fill {ARENA} minecraft:air replace']
    case = validate_scenario({'schema_version': 1, 'id': f'fuzz-{seed}',
        'title': f'Seed {seed} {mode} state machine', 'category': 'fuzz',
        'description': 'Bounded arithmetic and inert blocks with independent positive state oracles.',
        'tags': ['command', 'seeded', 'bounded'], 'setup': setup, 'steps': steps, 'cleanup': cleanup,
        'notes': 'Generator v1. Arena x/z 0..3, y=80. No client or elapsed-tick claim.'})
    return case, generated


def fuzz(targets_path, output, *, seed, seeds=10, actions=12, mode='mixed', max_seconds=300,
         max_probes=30, timeout=3, lock_timeout=10, versions_path=None, pumpkin_console=None):
    if type(seeds) is not int or not 1 <= seeds <= 20:
        raise ValueError('seeds must be between 1 and 20')
    if type(seed) is not int or seed < 0 or seed + seeds > 2**64:
        raise ValueError('seed range must fit unsigned 64-bit integers')
    if not 0 < max_seconds <= 900 or not 0 < timeout <= 5 or not 0 < lock_timeout <= 30:
        raise ValueError('seconds <=900, operation timeout <=5, lock timeout <=30; all must be positive')
    if type(max_probes) is not int or not 2 <= max_probes <= 60:
        raise ValueError('max-probes must be between 2 and 60')
    # Validation/generation precedes connection. Every action is saved before use.
    cases = [generate(s, actions, mode) for s in range(seed, seed + seeds)]
    targets = load_targets(targets_path)
    if versions_path is None:
        raise ValueError('fuzz requires explicit target versions')
    versions = load_versions(versions_path)
    _console_version(versions, pumpkin_console)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='fuzz-', dir=output))
    state = {'schema_version': 1, 'generator_version': 1, 'state': 'running', 'complete': False,
        'started_at': utc_now(), 'seed': seed, 'seeds': seeds, 'actions_per_seed': actions, 'mode': mode,
        'limits': {'max_seconds': max_seconds, 'cleanup_grace_seconds': 30, 'max_probes_total': max_probes,
                   'arena': {'x': [0,3], 'y': [80,80], 'z': [0,3]}, 'max_fill_volume': 16,
                   'repeat': 2, 'timeout': timeout, 'lock_timeout': lock_timeout},
        'target_versions': versions, 'runs': [], 'failures': [], 'reductions': [],
        'limitations': ['Command observations only; RCON binary provenance is declared, not attested.',
                        'Deadline allows bounded cleanup; no global shortest-reproducer claim.']}
    for case, generated in cases:
        atomic_json(directory / (case['id'] + '.json'), case)
        atomic_json(directory / (case['id'] + '-actions.json'), generated)
    atomic_json(directory / 'target-versions.json', versions)
    # Reset scores is redundant with setup; always successful and explicit for reducer.
    atomic_json(directory / 'reset.json', {'commands': ['scoreboard players reset #a', 'scoreboard players reset #b']})
    def save(): atomic_json(directory / 'fuzz-report.json', state)
    save()
    replay = [sys.executable, '-m', 'lab', 'fuzz', '--targets', str(Path(targets_path).resolve()),
        '--versions', str(directory / 'target-versions.json'), '--output', str(output),
        '--seed', str(seed), '--seeds', str(seeds), '--actions', str(actions), '--mode', mode,
        '--max-seconds', str(max_seconds), '--max-probes', str(max_probes),
        '--timeout', str(timeout), '--lock-timeout', str(lock_timeout)]
    if pumpkin_console:
        replay += ['--pumpkin-console', str(Path(pumpkin_console).resolve())]
    state['replay_argv'] = replay
    state['replay_cwd'] = str(Path(__file__).resolve().parents[1])
    state['replay_command'] = 'cd ' + shlex.quote(state['replay_cwd']) + ' && ' + shlex.join(replay)
    (directory / 'replay.txt').write_text(state['replay_command'] + '\n')
    started = time.monotonic()
    def check_budget():
        if time.monotonic() - started >= max_seconds:
            raise TimeoutError('Fuzz campaign time budget exhausted')
    try:
        with time_budget(max_seconds):
            for case, generated in cases:
                check_budget()
                load_versions(directory / 'target-versions.json')
                path, report, code = run([case], targets, directory / 'runs', repeat=2, timeout=timeout,
                    lock_timeout=lock_timeout, pumpkin_console=pumpkin_console,
                    console_arena=mode != 'scoreboard')
                result = report['results'][0]
                entry = {'seed': int(case['id'][5:]), 'run': str(path), 'exit_code': code,
                         'status': result['status'], 'classification': result.get('trial_details', {}).get('classification', 'incomplete')}
                state['runs'].append(entry)
                if code:
                    state['failures'].append({**entry, 'reason': result['reason'],
                                              'failure_identity': failure_identity(result)})
                save()
                check_budget()
                if code == 2:
                    raise RuntimeError('Infrastructure failure; campaign stopped with evidence')
            # All requested seeds run before spending the shared probe budget.
            remaining = max_probes
            for failure in state['failures']:
                check_budget()
                if not failure['failure_identity'] or remaining < 2:
                    continue
                path, reduction, code = shrink_scenario(directory / f'fuzz-{failure["seed"]}.json',
                    targets_path, directory / 'reductions', repeat=2, timeout=timeout, max_probes=remaining,
                    reset_path=directory / 'reset.json', versions_path=directory / 'target-versions.json',
                    lock_timeout=lock_timeout, pumpkin_console=pumpkin_console, console_arena=mode != 'scoreboard')
                remaining -= len(reduction['probes'])
                state['reductions'].append({'seed': failure['seed'], 'directory': str(path),
                    'minimized': reduction['minimized'], 'probes': len(reduction['probes']), 'exit_code': code})
                save()
                check_budget()
            state.update(state='finished', complete=True)
    except (Exception, KeyboardInterrupt) as exc:
        state.update(state='interrupted' if isinstance(exc, KeyboardInterrupt) else 'failed',
                     error={'kind': type(exc).__name__, 'reason': str(exc)})
    finally:
        state.update(finished_at=utc_now(), elapsed_seconds=round(time.monotonic()-started, 3))
        save()
    return directory, state, 2 if not state['complete'] else 1 if state['failures'] else 0
