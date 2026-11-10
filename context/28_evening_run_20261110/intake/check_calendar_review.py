#!/usr/bin/env python3
"""Exact EV-MR02 receipt and one readiness boundary, not a repeated review."""
import csv, hashlib, io, json, subprocess
from datetime import date
from pathlib import Path
REVIEW = '8cb5fde05c51ae05f7b72e3cb996f0cb4fa26550'
SUBJECT = 'aa7779192d809558e38b1eb9bdfa25913a3afdc8'
BASE = 'context/28_evening_run_20261110/'
R = BASE + 'calendar_budget_review/'
def blob(sha, path):
    return subprocess.check_output(['git', 'show', sha + ':' + path])
def obj(path):
    return json.loads(blob(REVIEW, R + path))
out = obj('review_manifest.json')
inputs = obj('subject_manifest.json')
handoff = obj('handoff.json')
findings = obj('findings.json')
probes = obj('verify/probes.json')
assert all(x['subject_sha'] == SUBJECT for x in [out, inputs, handoff, findings, probes])
for row in out['files']:
    b = blob(REVIEW, R + row['path'])
    assert len(b) == row['bytes'] and hashlib.sha256(b).hexdigest() == row['sha256']
for row in inputs['files']:
    b = blob(SUBJECT, row['path'])
    assert len(b) == row['bytes'] and hashlib.sha256(b).hexdigest() == row['sha256']
    assert subprocess.check_output(['git', 'rev-parse', SUBJECT + ':' + row['path']]).decode().strip() == row['git_blob']
assert handoff['verdict'] == findings['verdict'] == 'APPROVE_SCOPED'
assert not findings['critical_or_blocking_findings']
rows = list(csv.DictReader(io.StringIO(blob(SUBJECT, BASE + 'methods/runs/annual_v1/aircraft_calendar_daily.csv').decode())))
sample = [x for x in rows if x['branch'] == 'PHASED' and x['availability'] == 'NO_SCHEDULED_GROUNDING' and x['date'] in ['2027-07-30', '2027-07-31']]
assert len(sample) == 2
for row in sample:
    elapsed = (date.fromisoformat(row['date']) - date(2027, 7, 1)).days
    entered = 3 if elapsed >= 30 else 0
    assert int(row['entered_new']) == entered
    assert int(row['working_new']) == max(0, entered - 1)
    assert row['actual_RW_delivery_status'] == 'SCENARIO_NOT_CONFIRMED'
assert len(handoff['held_conclusions']) == 5
result = {
    'review_sha': REVIEW, 'subject_sha': SUBJECT,
    'status': 'APPROVE_SCOPED_RECEIPT_ADMITTED',
    'checks': {'review_output_hashes': len(out['files']), 'subject_blob_hashes_and_ids': len(inputs['files']),
               'independent_example': '30-day entry from July1: working0 July30, working2 July31 with scenario received3/reserve1'},
    'accepted_scope': handoff['accepted_scope'], 'held_conclusions': handoff['held_conclusions'],
    'review_reexecuted_by_root': False,
}
Path(__file__).with_name('calendar_review_checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ['review_sha', 'subject_sha', 'status', 'checks']}, ensure_ascii=False))
