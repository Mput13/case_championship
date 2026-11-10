"""Separate owner replay, after independent.py. Writes only the review runtime/logs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SUBJECT = HERE / '.runtime/subject'
env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
before = {r['path']:r['sha256'] for r in json.loads((SUBJECT/'output_manifest.json').read_text())['files']}
results = []
for script, args in [('annual_calendar.py', []), ('verify_calendar.py', []), ('support_budget.py', []), ('budget_conditions.py', []), ('package_manifest.py', ['--check'])]:
    proc = subprocess.run([sys.executable, '-B', str(SUBJECT/script), *args], env=env, capture_output=True, text=True, timeout=180)
    result = dict(script=script, arguments=args, exit_code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
    results.append(result)
    assert proc.returncode == 0, result
after = {path:hashlib.sha256((SUBJECT/path).read_bytes()).hexdigest() for path in before}
changed = [path for path in before if before[path] != after[path]]
assert not changed, changed
receipt = dict(status='PASS_OWNER_REPLAY_SEPARATE_FROM_INDEPENDENT', commands=results, unchanged_manifest_entries=len(before), changed_paths=changed,
    not_run=['selection_experiment.py / verify_selection.py: previous EV-MR01 scope', 'resource_construction.py: MILP not rerun; all serialized constructions independently validated', 'primary-source live verification and final evidence38f: separate reviewer'])
(HERE/'owner_replay.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='commands'}, indent=2))
