#!/usr/bin/env python3
"""Hash the completed review package; exclude this manifest's own bytes."""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
rows = []
for path in sorted(BASE.rglob('*')):
    if not path.is_file() or path.name == 'output_manifest.json' or 'pinned_png' in path.parts or '__pycache__' in path.parts:
        continue
    b = path.read_bytes()
    rows.append({'path':str(path.relative_to(BASE)), 'bytes':len(b), 'sha256':hashlib.sha256(b).hexdigest()})
manifest = {'schema':1,'review_id':'EV-DIGITAL-FINAL',
    'subject_sha':'d48b4a4f86de29aa968665f1601b785bd1824c54',
    'scope':'context/28_evening_run_20261110/digital_growth_review/',
    'artifacts':rows,'self_hash':'Excluded to avoid recursive hash',
    'temporary_png_copies':'Excluded; exact source hashes and own inspection are retained; verify.py can extract again.'}
(BASE/'output_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'artifacts':len(rows),'output':'output_manifest.json'}))
