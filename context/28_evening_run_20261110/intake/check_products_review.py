#!/usr/bin/env python3
"""Admit exact products review with cash and company-growth boundaries."""
import hashlib, json, math, subprocess
from functools import lru_cache
from pathlib import Path
REVIEW = '6cc8c37e23c89488f3113efd96952d13f253f274'
SUBJECT = '388908b6da3539484cb8e2e03ada6ff5cb2204a4'
ROOT = 'context/28_evening_run_20261110/products_review/'
@lru_cache(maxsize=None)
def blob(s,p): return subprocess.check_output(['git','show',s+':'+p])
def obj(p): return json.loads(blob(REVIEW,ROOT+p))
out = obj('manifests/output_manifest.json')
inputs = obj('manifests/input_manifest.json')
handoff = obj('manifests/handoff.json')
findings = obj('findings.json')
assert out['subject'] == inputs['subject'] == handoff['reviewed_sha'] == findings['reviewed_sha'] == SUBJECT
for r in out['files']:
    b=blob(REVIEW,ROOT+r['path'])
    assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
for r in inputs['files']:
    b=blob(r['commit'],r['path'])
    assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
assert handoff['verdict']==findings['verdict']=='APPROVE_SCOPED'
assert not findings['open_findings'] and not any(findings['severity_counts'].values())
report=blob(REVIEW,ROOT+'report.md').decode()
assert '498 260' in report and 'same-day' in report.lower()
assert '1 574 784' in report and '987 392' in report
# The independent review's concrete double-sale counterexample uses two alternatives.
assert 987392+587392==1574784
assert any('company-wide growth' in r['claim'] for r in findings['interpretation_limits'])
result={'review_sha':REVIEW,'subject_sha':SUBJECT,'status':'APPROVE_SCOPED_RECEIPT_ADMITTED',
        'checks':{'review_output_hashes':len(out['files']),'pinned_input_hashes':len(inputs['files']),
                  'real_counterexample':'987392 own-feed ceiling +587392 external-feed contribution duplicates shared journeys/seats'},
        'accepted_scope':handoff['acceptance_boundary'],
        'qualifications':['C35 incremental segment counter is not accepted as company-wide growth without old-trip segment counts',
                          'Same-day cash netting is a lower financing bound, not zero intraday need',
                          'Internal/external feed are alternatives; C31 joint allocation reviewed separately',
                          'C17 corrected 35+35 in both years; refusal conditional on named no-support recipe'],
        'review_reexecuted_by_root':False}
Path(__file__).with_name('products_review_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['status','review_sha','subject_sha','checks']},ensure_ascii=False))
