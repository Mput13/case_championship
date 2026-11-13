#!/usr/bin/env python3
"""Seal or verify this completed proposal package without altering child packages."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / 'output_manifest.json'
if '--verify' not in sys.argv:
    members = []
    for path in sorted(ROOT.rglob('*')):
        if path.is_file() and path != TARGET:
            assert '__pycache__' not in path.parts, path
            data = path.read_bytes()
            members.append({'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    TARGET.write_text(json.dumps({'scope': 'consensus proposal; conditional resource and source-grounded route cards', 'files': members}, ensure_ascii=False, indent=2) + '\n')
manifest = json.loads(TARGET.read_text())
for item in manifest['files']:
    data = (ROOT / item['path']).read_bytes()
    assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'], item['path']
assert {item['path'] for item in manifest['files']} == {str(path.relative_to(ROOT)) for path in ROOT.rglob('*') if path.is_file() and path != TARGET}
print(json.dumps({'status': 'PASS', 'files': len(manifest['files']), 'bytes': sum(item['bytes'] for item in manifest['files']), 'manifest_sha256': hashlib.sha256(TARGET.read_bytes()).hexdigest()}))
