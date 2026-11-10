#!/usr/bin/env python3
"""Seal explicitly, otherwise verify only this review package's file hashes."""
import hashlib
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parent
manifest=root/'output_manifest.json'
files=sorted(p for p in root.rglob('*') if p.is_file() and p!=manifest)
assert not any(p.is_symlink() for p in root.rglob('*'))
assert not any(p.is_dir() and (p.name.startswith('owner_replay_') or p.name=='__pycache__') for p in root.rglob('*'))

if sys.argv[1:]==['--seal']:
    data=dict(subject='ba9f6b85b4f8c9847948ae428ef3fbcfca9e2009',
              prepared_root='c43e58569f3fc561bb7d0dd0806995b718ef01a9',
              scope='context/23_night_run_20261110/allocation_variants_review/',
              self_excluded='output_manifest.json',
              files=[dict(path=str(p.relative_to(root)),bytes=p.stat().st_size,
                          sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
    manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
else:
    assert not sys.argv[1:], 'usage: verify_package.py [--seal]'
    data=json.loads(manifest.read_text())
    assert {str(p.relative_to(root)) for p in files}=={r['path'] for r in data['files']}
    for r in data['files']:
        assert Path(r['path']).is_relative_to('.') and '..' not in Path(r['path']).parts
        p=root/r['path']
        assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],r['path']
    checks=json.loads((root/'independent_checks.json').read_text())
    assert checks['status']=='PASS_SCOPED' and checks['primary']==48 and checks['secondary']==32
    findings=json.loads((root/'findings.json').read_text())
    assert findings['verdicts']=={'A':'APPROVE_SCOPED','B':'APPROVE_SCOPED'} and findings['findings']==[]
print(json.dumps(dict(status='PASS_PACKAGE_HASHES',files=len(data['files']),bytes=sum(r['bytes'] for r in data['files']))))
