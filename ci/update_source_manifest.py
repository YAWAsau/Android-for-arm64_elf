"""Refresh source manifests after staging intended additions/removals; never stages files."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
git = ['git', '-c', 'safe.directory=' + str(ROOT)]
top = Path(subprocess.check_output(git + ['rev-parse', '--show-toplevel'], cwd=ROOT).decode().strip()).resolve()
if top != ROOT.resolve():
    raise SystemExit('Wrong Git root')
names = sorted(filter(None, subprocess.check_output(git + ['ls-files', '-z'], cwd=ROOT).decode('utf8').split('\0')))
manifest = ROOT / 'SOURCE_MANIFEST.json'
data = json.loads(manifest.read_text(encoding='utf8'))
data['files'] = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in names
                 if n not in ('SOURCE_MANIFEST.json', 'SOURCE_SHA256SUMS.txt')}
manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')
(ROOT / 'SOURCE_SHA256SUMS.txt').write_text(''.join(hashlib.sha256((ROOT / n).read_bytes()).hexdigest() + '  ' + n + '\n'
    for n in names if n != 'SOURCE_SHA256SUMS.txt'), encoding='utf8', newline='\n')
print('Updated source manifests; index unchanged')
