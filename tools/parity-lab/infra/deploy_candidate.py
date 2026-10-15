#!/usr/bin/env python3
"""Install a verified local source build into the private Pumpkin candidate only."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile

from provision import RUNTIME, control, digest, systemctl, write

WORKTREE=Path('/root/pumpkin-parity-worktrees/jaron')
DROPIN=Path('/etc/systemd/system/pumpkin-parity-pumpkin.service.d/50-source-build.conf')


def main():
    def interrupted(signum,frame):
        raise InterruptedError('Candidate deployment interrupted')
    signal.signal(signal.SIGTERM,interrupted)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--build-command',required=True)
    args=parser.parse_args()
    binary=args.binary.resolve(strict=True)
    head=subprocess.check_output(['git','-C',str(WORKTREE),'rev-parse','HEAD'],text=True).strip()
    dirty=subprocess.check_output(['git','-C',str(WORKTREE),'status','--porcelain','--untracked-files=no'],text=True)
    if dirty:
        raise RuntimeError('Commit source changes before deploying a reproducible build')
    stamp=datetime.datetime.now(datetime.UTC).strftime('%Y%m%dT%H%M%S.%fZ')
    backup=RUNTIME/'candidate-backups'/stamp
    lock_path=Path(tempfile.gettempdir())/f'pumpkin-parity-lab-{os.getuid()}.lock'
    with lock_path.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        backup.mkdir(parents=True,mode=0o700)
        for path in [RUNTIME/'manifest.json',RUNTIME/'pumpkin/pumpkin.toml',DROPIN]:
            if path.exists():
                shutil.copy2(path,backup/path.name)
                (backup/path.name).chmod(0o600)
        destination=RUNTIME/'downloads'/f'pumpkin-source-{head}'
        temporary=destination.with_suffix('.part')
        shutil.copy2(binary,temporary)
        temporary.chmod(0o755)
        temporary.replace(destination)
        source_digest=digest(binary,'sha256')
        if digest(destination,'sha256') != source_digest:
            raise RuntimeError('Installed binary checksum differs from build output')
        systemctl('stop','pumpkin')
        try:
            write(DROPIN,f'[Service]\nExecStart=\nExecStart={destination}\n',0o644)
            systemctl('daemon-reload')
            systemctl('start','pumpkin')
            targets=json.loads((RUNTIME/'targets.json').read_text())['targets']
            control('pumpkin',targets['pumpkin'],readiness_seconds=20)
            manifest=json.loads((RUNTIME/'manifest.json').read_text())
            manifest['active_candidate']={
                'kind':'source-build','source_commit':head,'branch':'parity-lab-jaron',
                'upstream':'https://github.com/Pumpkin-MC/Pumpkin.git',
                'binary':str(destination.relative_to(RUNTIME.parent)),
                'sha256':source_digest,'build_command':args.build_command,
                'deployed_at':datetime.datetime.now(datetime.UTC).isoformat(),
                'backup':str(backup.relative_to(RUNTIME.parent)),
                'validation':'RCON and controlled gamerules verified; world/scenario results recorded separately',
            }
            write(RUNTIME/'manifest.json',json.dumps(manifest,indent=2)+'\n',0o644)
        except BaseException:
            systemctl('stop','pumpkin')
            shutil.copy2(backup/'pumpkin.toml',RUNTIME/'pumpkin/pumpkin.toml')
            previous=backup/DROPIN.name
            if previous.exists():
                shutil.copy2(previous,DROPIN)
                DROPIN.chmod(0o644)
            else:
                DROPIN.unlink(missing_ok=True)
            systemctl('daemon-reload')
            systemctl('start','pumpkin')
            raise
    print(json.dumps(manifest['active_candidate'],indent=2))


if __name__=='__main__':
    main()
