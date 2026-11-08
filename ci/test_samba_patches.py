"""Exercise the actual patch composition on pinned upstream source files."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'samba/tools/samba_android'
MANIFEST = json.loads((TOOLS / 'patch-manifest.json').read_text())


class SambaPatches(unittest.TestCase):
    def test_composition_and_drift(self):
        archive = ROOT / 'samba/upstream-source/samba-4.25.1.tar.gz'
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), MANIFEST['archive_sha256'])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with tarfile.open(archive) as tf:
                for name in MANIFEST['files']:
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(tf.extractfile('samba-4.25.1/' + name).read())
            command = [sys.executable, str(TOOLS / 'apply-patches.py'), str(root)]
            os.environ['PYTHONUTF8'] = '1'
            def run():
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            run()
            first = {name: (root / name).read_bytes() for name in MANIFEST['files']}
            run()
            self.assertEqual(first, {name: (root / name).read_bytes() for name in MANIFEST['files']})
            audit = json.loads((ROOT / 'verification/samba-4251-publisher-20261108.json').read_text())
            for name, expected in audit['baseline_files'].items():
                self.assertEqual(hashlib.sha256((root / name).read_text().encode()).hexdigest(), expected, name)
            # Tampering with an already-patched file must fail before any edit.
            client = root / 'source3/client/client.c'
            client.write_bytes(client.read_bytes() + b'\n/* unexpected drift */\n')
            before = {name: (root / name).read_bytes() for name in MANIFEST['files']}
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Source drift:', result.stderr)
            self.assertEqual(before, {name: (root / name).read_bytes() for name in MANIFEST['files']})


if __name__ == '__main__':
    unittest.main()
