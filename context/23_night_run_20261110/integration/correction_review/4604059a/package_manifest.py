#!/usr/bin/env python3
"""Hash the small, safe MR10 review files; manifest excludes only itself."""
import csv
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = []
for p in sorted(ROOT.iterdir()):
    if not p.is_file() or p.name == 'output_manifest.json':
        continue
    b = p.read_bytes()
    item = dict(path=p.name, sha256=hashlib.sha256(b).hexdigest(), bytes=len(b))
    if p.suffix == '.csv':
        rr = list(csv.DictReader(io.StringIO(b.decode('utf-8'))))
        item.update(rows=len(rr), grain={
            'independent_lineage_join.csv': 'one affected SVX dated publication row with upstream source-line FK',
            'held_clock_mappings.csv': 'one preserved exact-clock HOLD card-to-candidate mapping',
            'independent_timestamps.csv': 'one physical leg departure or arrival UTC event',
            'independent_rotation_conflicts.csv': 'one conflicting adjacent pair for fixed planning label; scenario-independent',
            'independent_conservation.csv': 'network × author scenario × disruption policy',
            'bounded_day1_replay.csv': 'network × author scenario × disruption policy; author numeric replay before gating'
        }[p.name])
    else:
        item['grain'] = 'review metadata / executable check / evidence receipt / narrative'
    FILES.append(item)
manifest = dict(package_id='MR10-independent-correction-review-20261110-v1',
                safe_scope='context/23_night_run_20261110/correction_review/',
                excluded_self='output_manifest.json', files=FILES,
                raw_auth_contacts_dependencies='NOT_INCLUDED', acceptance='SEPARATE_APPROVE_SCOPED_FOR_A_AND_B')
(ROOT / 'output_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(dict(files=len(FILES),bytes=sum(f['bytes'] for f in FILES)),ensure_ascii=False))
