#!/usr/bin/env python3
"""Live expectation validation with the independent probe, not an engine verdict.

Raw responses are retained. No error-message equality can satisfy a positive
expectation. This validates the vanilla baseline even if the lab transport fails.
"""
import argparse
import datetime
import fcntl
import json
import os
import sys
from pathlib import Path
import tempfile
try:
    from .rcon_probe import ROOT, Rcon
except ImportError:
    from rcon_probe import ROOT, Rcon

# Direct script execution and module execution share the same schema checks.
sys.path.insert(0,str(ROOT))
from infra.catalog import load_catalog


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',choices=['vanilla','pumpkin','both'],default='vanilla')
    parser.add_argument('--id',action='append')
    parser.add_argument('--repeat',type=int,default=1)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    targets=json.loads((ROOT/'runtime/targets.json').read_text())['targets']
    scenarios=load_catalog(ROOT/'scenarios')
    if args.id:
        scenarios=[s for s in scenarios if s['id'] in args.id]
        if {s['id'] for s in scenarios} != set(args.id):
            raise ValueError('Unknown scenario id')
    if args.repeat < 1 or not scenarios:
        raise ValueError('Expected nonempty scenarios and positive repeat')
    report={'schema_version':1,'kind':'independent-expectation-validation',
            'started_at':datetime.datetime.now(datetime.UTC).isoformat(),
            'complete':False,'scenarios':scenarios,'results':[]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():
        temporary=args.output.with_name(args.output.name+'.tmp')
        temporary.write_text(json.dumps(report,indent=2)+'\n')
        temporary.replace(args.output)
    save()
    lock_path=Path(tempfile.gettempdir())/f'pumpkin-parity-lab-{os.getuid()}.lock'
    with lock_path.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        for name,target in targets.items():
            if args.target not in ('both',name):
                continue
            for attempt in range(1,args.repeat+1):
                client=Rcon(target)
                try:
                    for scenario in scenarios:
                        result={'id':scenario['id'],'target':name,'repeat':attempt,
                                'complete':False,'expectations_met':False,'events':[]}
                        report['results'].append(result)
                        def execute(command,phase,step=None):
                            event={'phase':phase,'command':command}
                            result['events'].append(event)
                            try:
                                raw=client.command(command)
                            except Exception as exc:
                                event['error']=f'{type(exc).__name__}: {exc}'
                                save()
                                raise
                            event['response']=raw
                            if step and step.get('observe'):
                                event['expect_contains']=step['expect_contains']
                                event['expectation_met']=step['expect_contains'] in raw
                            save()
                        try:
                            for command in scenario['setup']:
                                execute(command,'setup')
                            for step in scenario['steps']:
                                if step.get('wait_ticks',0):
                                    raise ValueError('Independent validator does not simulate ticks; use lab engine')
                                execute(step['command'],'steps',step)
                        finally:
                            for command in scenario['cleanup']:
                                execute(command,'cleanup')
                        result['complete']=True
                        observed=[e for e in result['events'] if 'expectation_met' in e]
                        result['expectations_met']=bool(observed) and all(e['expectation_met'] for e in observed)
                        save()
                        print(name,attempt,scenario['id'],'expectations-met' if result['expectations_met'] else 'EXPECTATION-FAILED',flush=True)
                finally:
                    client.close()
    report['complete']=True
    report['finished_at']=datetime.datetime.now(datetime.UTC).isoformat()
    report['summary']={'total':len(report['results']),
                       'expectations_met':sum(r['expectations_met'] for r in report['results'])}
    save()
    print(json.dumps(report['summary']))
    return 0 if all(r['expectations_met'] for r in report['results']) else 1

if __name__=='__main__':
    raise SystemExit(main())
