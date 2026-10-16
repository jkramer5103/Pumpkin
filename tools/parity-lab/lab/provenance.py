"""Allowlisted, declared target provenance with verified local file identities."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path


class ProvenanceError(ValueError):
    pass


def binary_identity(path):
    path = Path(path).resolve(strict=True)
    with path.open('rb') as handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
    return {'binary': str(path), 'sha256': digest}


def world_identity(path):
    path = Path(path).resolve(strict=True)
    if not path.is_dir():
        raise ProvenanceError('World path must be a directory')
    info = path.stat()
    return {'path': str(path), 'device': info.st_dev, 'inode': info.st_ino}


def verify_versions(value):
    """Return a safe copy, pinning hashes and optional world directory identities.

    Local directory identity cannot prove world contents, seeds, or which world
    an RCON service has loaded. Do not copy arbitrary runtime manifests here.
    """
    value = copy.deepcopy(value)
    if not isinstance(value, dict) or set(value) != {'vanilla', 'pumpkin'}:
        raise ProvenanceError('Versions must contain exactly vanilla and pumpkin')
    for name, version in value.items():
        if not isinstance(version, dict) or not version.get('version'):
            raise ProvenanceError(f'{name} requires a version')
        if set(version) - {'version', 'source_commit', 'binary', 'sha256', 'transport', 'world'}:
            raise ProvenanceError('Unrecognized version metadata; do not include credentials')
        if any(not isinstance(v, str) or not v.strip() for k, v in version.items() if k != 'world'):
            raise ProvenanceError('Version metadata values must be nonempty strings')
        if 'binary' in version:
            identity = binary_identity(version['binary'])
            if 'sha256' in version and version['sha256'] != identity['sha256']:
                raise ProvenanceError(f'{name} binary hash differs from recorded version')
            version.update(identity)
        if 'world' in version:
            world = version['world']
            if (not isinstance(world, dict) or 'path' not in world
                    or set(world) - {'path', 'device', 'inode'}
                    or not isinstance(world['path'], str) or not world['path'].strip()
                    or any(type(world[k]) is not int for k in ('device', 'inode') if k in world)):
                raise ProvenanceError('World metadata requires path and optional integer device/inode')
            identity = world_identity(world['path'])
            if any(world[k] != identity[k] for k in ('device', 'inode') if k in world):
                raise ProvenanceError(f'{name} world directory identity differs from recorded version')
            version['world'] = identity
    return value


def check_transports(versions, pumpkin_console):
    for name in ('vanilla', 'pumpkin'):
        transport = 'scratch-console' if name == 'pumpkin' and pumpkin_console else 'rcon'
        if versions[name].get('transport', transport) != transport:
            raise ProvenanceError(f'{name} version transport differs from selected transport')
    if pumpkin_console is not None:
        if versions['pumpkin'].get('binary') != str(Path(pumpkin_console).resolve()):
            raise ProvenanceError('Console binary must match the Pumpkin versions record')
