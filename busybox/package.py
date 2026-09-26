"""Package the completed ELF together with its corresponding source and recipe."""
from pathlib import Path
import hashlib
import json
import re
import zipfile
from build import recipe_hash

root=Path(__file__).resolve().parent
manifest=json.loads((root/'out/BUILD_MANIFEST.json').read_text())
digest=hashlib.sha256((root/'out/busybox').read_bytes()).hexdigest()
if manifest['elf']['sha256'] != digest:
    raise SystemExit('Binary differs from build manifest; rebuild before packaging.')
if manifest['recipe_sha256'] != recipe_hash():
    raise SystemExit('Build recipe changed after compilation; rebuild before packaging.')
destination=root.parent/'dist'
destination.mkdir(exist_ok=True)
profile=manifest['build_profile']
if not re.fullmatch(r'[a-z0-9][a-z0-9-]*',profile):
    raise SystemExit('Invalid build profile name.')
suffix='-'+profile if profile != 'full' else ''
target=destination/('busybox-1.38.0-android-arm64-ndkr30-api28-lto'+suffix+'-build-kit.zip')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for p in sorted(root.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            archive.write(p,p.relative_to(root).as_posix())
target.with_suffix('.zip.sha256').write_text(hashlib.sha256(target.read_bytes()).hexdigest()+'  '+target.name+'\n')
print(target)
