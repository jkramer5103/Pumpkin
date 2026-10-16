"""Finite catalog gaps: ordered list edits, copied data, and all-objective reset."""
from copy import deepcopy
import json
from pathlib import Path

from infra.author_scenarios import CLEAR, SEL, ONE


def probe(conditions):
    return {'command': 'execute '+conditions, 'observe': True, 'expect_contains': 'Test passed'}


def read_list(path, expected):
    # Selector NBT lists are unordered subsets. Numeric data-get results prove
    # list length and index order instead; sentinels prevent silent stores passing.
    commands = []
    checks = []
    for holder, suffix, value in [('length', '', len(expected))]+[
            (f'index{i}', f'[{i}]', value) for i, value in enumerate(expected)]:
        commands += [f'scoreboard players set {holder} pp_audit -9999',
                     f'execute store result score {holder} pp_audit run data get entity {ONE} {path}{suffix}']
        checks.append(f'if score {holder} pp_audit matches {value}')
    return commands+[probe(' '.join(checks))]


def audit_cases():
    cases = []
    kill = f'execute if entity {SEL} run kill {SEL}'
    for identity, title, description, mutation, result in [
        ('entity-nbt-prepend', 'Prepend shifts existing list elements',
         'Prepending eight puts it before two and four, preserving the exact three-element order.',
         'data.values prepend value 8', [8, 2, 4]),
        ('entity-nbt-insert-negative-index', 'Negative insertion indexes count from the list end',
         'Inserting at minus two puts eight before the last member, rather than appending or replacing it.',
         'data.values insert -2 value 8', [2, 8, 4]),
        ('entity-nbt-copy-isolation', 'Copied NBT lists remain independent',
         'Copying a list and replacing its first member leaves the original list unchanged.',
         f'data.copy set from entity {ONE} data.values', [9, 4]),
    ]:
        commands = [f'summon minecraft:marker 2 64 2 {{Tags:["pp"],data:{{values:[2,4]}}}}']
        commands += read_list('data.values', [2, 4])
        commands.append(f'data modify entity {ONE} {mutation}')
        path = 'data.values'
        if identity == 'entity-nbt-copy-isolation':
            commands.append(f'data modify entity {ONE} data.copy[0] set value 9')
            commands += read_list('data.values', [2, 4])
            path = 'data.copy'
        commands += read_list(path, result)
        cases.append({
            'schema_version': 1, 'id': identity, 'title': title, 'category': 'entity-nbt',
            'description': description, 'tags': ['command', 'deterministic', 'state-observation'],
            'setup': ['tick freeze', kill, CLEAR, 'scoreboard objectives add pp_audit dummy'],
            'steps': [{'command': c} if isinstance(c, str) else c for c in commands],
            'cleanup': [kill, 'scoreboard objectives remove pp_audit', CLEAR, 'tick unfreeze'],
            'notes': 'Requires execute store result and indexed data get; missing support is visible. '
                     'Initial list and final length/every index are positively observed. No client or elapsed-tick claim.'})
    cases.append({
        'schema_version': 1, 'id': 'score-reset-all-objectives',
        'title': 'Reset without objective removes all holder scores', 'category': 'scoreboard',
        'description': 'Resetting one holder without an objective removes both its scores while preserving another holder in both objectives.',
        'tags': ['command', 'deterministic', 'state-observation'],
        'setup': ['tick freeze', 'scoreboard objectives add pp_audit dummy', 'scoreboard objectives add pp_other dummy'],
        'steps': [{'command': c} for c in [
            'scoreboard players set cleared pp_audit 7', 'scoreboard players set cleared pp_other 9',
            'scoreboard players set survivor pp_audit 11', 'scoreboard players set survivor pp_other 13']]+[
                probe('if score cleared pp_audit matches 7 if score cleared pp_other matches 9'),
                {'command': 'scoreboard players reset cleared'},
                probe('if score survivor pp_audit matches 11 if score survivor pp_other matches 13 '
                      'unless score cleared pp_audit matches -2147483648..2147483647 '
                      'unless score cleared pp_other matches -2147483648..2147483647')],
        'cleanup': ['scoreboard objectives remove pp_other', 'scoreboard objectives remove pp_audit', 'tick unfreeze'],
        'notes': 'Frozen command-state test with positive before/after controls; no real-player score or persistence claim.'})
    return deepcopy(cases)


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]/'scenarios'
    for scenario in audit_cases():
        (root/(scenario['id']+'.json')).write_text(json.dumps(scenario, indent=2)+'\n')
