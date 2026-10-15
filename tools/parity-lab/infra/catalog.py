"""Validate authoring invariants in addition to the engine's scenario schema."""
from pathlib import Path
import json

from lab.schema import SchemaError, validate_scenario


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


def load_catalog(directory):
    return validate_catalog([json.loads(path.read_text()) for path in sorted(Path(directory).glob('*.json'))])


if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    print(f'Validated {len(load_catalog(root/"scenarios"))} distinct scenarios')
