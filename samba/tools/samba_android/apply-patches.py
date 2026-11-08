"""Apply the reviewed composition; reject drift before editing any source file."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_text(encoding='utf8').encode()).hexdigest()


def main():
    root = Path(sys.argv[1])
    manifest = json.loads((HERE / 'patch-manifest.json').read_text())
    for name, hashes in manifest['files'].items():
        path = root / name
        if not path.is_file() or digest(path) not in hashes.values():
            raise SystemExit('Source drift: ' + name + '; use a fresh cache or -Clean')
    subprocess.run([sys.executable, str(HERE / 'patch-samba.py'), str(root)], check=True)
    for name, hashes in manifest['files'].items():
        if digest(root / name) != hashes['patched']:
            raise SystemExit('Incomplete patch composition: ' + name)
    print('Verified complete Samba 4.25.1 Android/publisher/pipe patch set')


if __name__ == '__main__':
    main()
