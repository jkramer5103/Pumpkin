#!/usr/bin/env python3
"""Serialize lifecycle actions against engine runs, and verify readiness on start."""
import argparse
import fcntl
import os
from pathlib import Path
import tempfile
try:
    from .provision import RUNTIME, SERVICES, control, systemctl
except ImportError:
    from provision import RUNTIME, SERVICES, control, systemctl
import json


def transition(action, names):
    """Apply a transition; caller must hold the shared engine process lock."""
    systemctl(action,*names)
    if action!='stop':
        targets=json.loads((RUNTIME/'targets.json').read_text())['targets']
        for name in names:
            control(name,targets[name])
            print(name+': RCON ready, controlled gamerules verified',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['start','stop','restart'])
    parser.add_argument('target',choices=['vanilla','pumpkin','both'],default='both',nargs='?')
    args=parser.parse_args()
    names=list(SERVICES) if args.target=='both' else [args.target]
    path=Path(tempfile.gettempdir())/f'pumpkin-parity-lab-{os.getuid()}.lock'
    with path.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        transition(args.action,names)

if __name__=='__main__':
    main()
