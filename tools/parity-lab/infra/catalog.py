"""Validate authoring invariants in addition to the engine's scenario schema."""
from pathlib import Path

from lab.schema import SchemaError, read_json, validate_scenario


def validate_catalog(scenarios):
    """Reject duplicate identities/command sequences and unchecked observations."""
    if not scenarios:
        raise SchemaError('catalog: no scenarios')
    ids=set()
    sequences={}
    for scenario in scenarios:
        validate_scenario(scenario)
        identity=scenario['id']
        if identity in ids:
            raise SchemaError(f'catalog: duplicate scenario id {identity}')
        ids.add(identity)
        # Metadata, expectations and cleanup cannot disguise the same experiment.
        sequence=(tuple(scenario['setup']),
                  tuple((step['command'],step.get('wait_ticks',0)) for step in scenario['steps']))
        if sequence in sequences:
            raise SchemaError(f'catalog: duplicate command sequence: {sequences[sequence]} and {identity}')
        sequences[sequence]=identity
        for index,step in enumerate(scenario['steps']):
            if step.get('observe') and not step.get('expect_contains','').strip():
                raise SchemaError(f'{identity}.steps[{index}]: every observation needs a positive expect_contains')
    return scenarios


def load_catalog(directory, *, recursive=False):
    directory = Path(directory)
    if not directory.is_dir():
        raise SchemaError(f'{directory}: scenario directory does not exist')
    paths = directory.rglob('*.json') if recursive else directory.glob('*.json')
    return validate_catalog([read_json(path) for path in sorted(paths)])


if __name__=='__main__':
    import argparse
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenarios',type=Path,default=root/'scenarios')
    parser.add_argument('--recursive',action='store_true',help='also validate opt-in catalogs and cross-directory identities')
    args=parser.parse_args()
    print(f'Validated {len(load_catalog(args.scenarios,recursive=args.recursive))} scenario definitions (unique IDs and command sequences)')
