#!/usr/bin/env python3
"""Verify the reviewer package. --write updates only its local output manifest."""
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
manifest = ROOT / 'output_manifest.json'
rows = []
for p in sorted(ROOT.rglob('*')):
    if not p.is_file() or p == manifest or any(x in ('.runtime', '__pycache__') for x in p.relative_to(ROOT).parts):
        continue
    raw = p.read_bytes()
    rows.append(dict(path=p.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)))
if '--write' in sys.argv:
    manifest.write_text(json.dumps(dict(subjectSHA='48686bf2276c435d7a260f4de6741c9b65d26e32', files=rows), indent=2) + '\n')
else:
    assert rows == json.loads(manifest.read_text())['files'], 'review output manifest mismatch'
    h = json.loads((ROOT/'handoff.json').read_text())
    f = json.loads((ROOT/'findings.json').read_text())
    s = json.loads((ROOT/'evidence/summary.json').read_text())
    assert h['subjectSHA'] == f['subjectSHA'] == s['subjectSHA'] == '48686bf2276c435d7a260f4de6741c9b65d26e32'
    assert h['verdict'] == f['verdict'] == 'APPROVE_SCOPED' and not f['blocking_findings']
    assert s['status'] == 'PASS_INDEPENDENT_SCOPED'
    assert (s['original_author_rounded_checks'], s['exact_oms_fixtures'], s['networks_independent_raw_flow_and_ledger'], s['frontier']['rows']) == (72, 3, 384, 303)
    assert all(x['rejected'] for x in s['counterexamples'])
print(json.dumps(dict(status='WRITTEN' if '--write' in sys.argv else 'PASS_REVIEW_PACKAGE', files=len(rows))))
