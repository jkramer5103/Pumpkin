"""Resolve pinned MCProtocolLib and compile; all tools/cache/output stay in runtime/."""
from pathlib import Path
import hashlib
import json
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / 'runtime/client-smoke'
MAVEN_VERSION = '3.9.11'
MAVEN_SHA512 = 'bcfe4fe305c962ace56ac7b5fc7a08b87d5abd8b7e89027ab251069faebee516b0ded8961445d6d91ec1985dfe30f8153268843c89aa392733d1a3ec956c9978'


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    maven = CACHE / f'apache-maven-{MAVEN_VERSION}/bin/mvn'
    if not maven.exists():
        url = f'https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/{MAVEN_VERSION}/apache-maven-{MAVEN_VERSION}-bin.tar.gz'
        data = urllib.request.urlopen(url, timeout=30).read()
        if hashlib.sha512(data).hexdigest() != MAVEN_SHA512:
            raise ValueError('Maven archive SHA-512 mismatch')
        archive = CACHE / 'maven.tar.gz'
        archive.write_bytes(data)
        with tarfile.open(archive) as tar:
            tar.extractall(CACHE, filter='data')
    classpath = CACHE / 'classpath.txt'
    subprocess.run([str(maven), '-B', '-f', str(Path(__file__).with_name('pom.xml')),
        f'-Dmaven.repo.local={CACHE / "m2"}',
        'org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath',
        f'-Dmdep.outputFile={classpath}'], check=True, timeout=480)
    # Freeze the actual transitive graph, including the protocol jar. A version
    # string alone does not detect a repository replacing a published artifact.
    expected = json.loads(Path(__file__).with_name('dependencies.sha256.json').read_text())
    actual = {str(Path(p).relative_to(CACHE / 'm2')): hashlib.sha256(Path(p).read_bytes()).hexdigest()
              for p in classpath.read_text().strip().split(':')}
    if actual != expected:
        raise ValueError('Client dependency graph/hash changed; inspect before updating the lock')
    classes = CACHE / 'classes'
    classes.mkdir(exist_ok=True)
    subprocess.run(['javac', '-cp', classpath.read_text().strip(), '-d', str(classes),
                    str(Path(__file__).with_name('ClientSmoke.java'))], check=True, timeout=60)
    print(classes)


if __name__ == '__main__':
    main()
