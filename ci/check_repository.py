"""Check the full ELF source repository; optional artifacts need no upstream import."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
from verify_smb_rng import verify

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ('zstd', 'tar', 'busybox', 'smbclient', 'smbd', 'samba-dcerpcd',
         'rpcd_classic', 'rpcd_lsad', 'rpcd_winreg')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifacts', type=Path, help='Also verify all nine built ELF files and SHA256SUMS.txt')
    args = parser.parse_args()
    git = ['git', '-c', 'safe.directory=' + str(ROOT)]
    top = Path(subprocess.check_output(git + ['rev-parse', '--show-toplevel'], cwd=ROOT).decode().strip()).resolve()
    require(top == ROOT.resolve(), 'Wrong Git root')
    names = set(filter(None, subprocess.check_output(git + ['ls-files', '-z'], cwd=ROOT).decode('utf8').split('\0')))
    require(names and all((ROOT / n).is_file() for n in names), 'Tracked file missing')
    manifest = json.loads((ROOT / 'SOURCE_MANIFEST.json').read_text(encoding='utf8'))['files']
    require(set(manifest) == names - {'SOURCE_MANIFEST.json', 'SOURCE_SHA256SUMS.txt'}, 'Source manifest must describe the entire tracked source set')
    for name, digest in manifest.items():
        require(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, 'Source SHA mismatch: ' + name)
    sums = {}
    for line in (ROOT / 'SOURCE_SHA256SUMS.txt').read_text(encoding='utf8').splitlines():
        digest, name = line.split('  ', 1)
        require(name not in sums and name in names, 'Invalid source checksum entry: ' + name)
        require(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, 'Checksum mismatch: ' + name)
        sums[name] = digest
    require(set(sums) == names - {'SOURCE_SHA256SUMS.txt'}, 'Incomplete source checksums')
    for folder in ('tar/upstream/', 'zstd/upstream/', 'busybox/upstream/', 'samba/upstream-source/'):
        require(any(n.startswith(folder) for n in names), 'Required upstream sources missing: ' + folder)
    require((ROOT / 'ci/verify_smb_rng.py').read_bytes() == (ROOT / 'samba/tools/samba_android/verify-rng-elf.py').read_bytes(), 'Standalone component and CI RNG guards diverged')
    subprocess.run([sys.executable, str(ROOT / 'ci/check_whitespace.py'), '--repository'], cwd=ROOT, check=True)
    if args.artifacts:
        sums = {}
        for line in (args.artifacts / 'SHA256SUMS.txt').read_text(encoding='utf8').splitlines():
            digest, name = line.split('  ', 1)
            require(name in TOOLS and name not in sums, 'Unexpected/duplicate artifact: ' + name)
            sums[name] = digest
        require(set(sums) == set(TOOLS), 'Expected all nine artifact checksums')
        for name in TOOLS:
            binary = args.artifacts / name
            require(hashlib.sha256(binary.read_bytes()).hexdigest() == sums[name], 'Artifact SHA mismatch: ' + name)
            verify(binary)
    print('PASS full tracked source/SHA/upstream inputs and repository whitespace' + ('; nine static RNG artifacts' if args.artifacts else '; binaries not rebuilt or tested'))


if __name__ == '__main__':
    main()
