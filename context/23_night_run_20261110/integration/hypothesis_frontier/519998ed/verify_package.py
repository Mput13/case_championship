#!/usr/bin/env python3
"""Check publication manifest and scope without mutating any research output."""
from pathlib import Path
import json, hashlib, subprocess

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
manifest=json.loads((ROOT/'output_manifest.json').read_text())
expected={r['path'] for r in manifest['files']}
actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p.name!='output_manifest.json'}
assert expected==actual,(expected-actual,actual-expected)
for r in manifest['files']:
    b=(ROOT/r['path']).read_bytes()
    assert hashlib.sha256(b).hexdigest()==r['sha256'] and len(b)==r['bytes'],r['path']
handoff=json.loads((ROOT/'handoff.json').read_text())
checks=json.loads((ROOT/'self_checks.json').read_text())
assert handoff['run_id']==checks['run_id']==manifest['run_id']
assert handoff['delivered']['classified']==35 and handoff['delivered']['selected_tests']==3
assert checks['pass_count']==36 and checks['fail_count']==0
assert handoff['independent_review'].startswith('PENDING')
assert all(not handoff['publication'][x] for x in ['force','merge','rebase','pull_request'])
from datetime import datetime
assert datetime.fromisoformat(handoff['completed_at_utc']) < datetime.fromisoformat(handoff['first_package_deadline_msk']), 'First-package deadline missed: report honestly instead of rewriting timestamp'
branch=subprocess.check_output(['git','branch','--show-current'],cwd=REPO,text=True).strip()
assert branch==handoff['publication']['branch'],branch
paths=subprocess.check_output(['git','diff','--name-only','f1774e1f66a9483fb618ca6003abd9dc4d8563e1'],cwd=REPO,text=True).splitlines()
assert all(p.startswith('context/23_night_run_20261110/hypothesis_frontier/') for p in paths),paths
print(json.dumps(dict(manifest_files=len(expected),bytes=manifest['bytes'],self_checks=36,branch=branch,first_package_before_0800_msk=True,independent_review='PENDING',git_scope='OWN_FOLDER_ONLY')))
