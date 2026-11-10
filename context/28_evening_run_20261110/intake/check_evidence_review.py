#!/usr/bin/env python3
"""Admit exact source-review receipt; retain inherited provenance limitation."""
import csv, hashlib, io, json, subprocess
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REVIEW = '13f7c373954cc16b33a53b7c46436ee3f15f753b'
SUBJECT = '38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b'
BASE = 'context/28_evening_run_20261110/'
R = BASE + 'evidence_review/'
S = BASE + 'evidence/'
def blob(sha, path):
    return subprocess.check_output(['git', 'show', sha + ':' + path])
def obj(sha, path):
    return json.loads(blob(sha, path))
def rows(path):
    return list(csv.DictReader(io.StringIO(blob(SUBJECT, S + path).decode())))

out = obj(REVIEW, R + 'output_manifest.json')
inputs = obj(REVIEW, R + 'input_manifest.json')
handoff = obj(REVIEW, R + 'handoff.json')
findings = obj(REVIEW, R + 'findings.json')
verification = obj(REVIEW, R + 'verification.json')
assert all(x['reviewed_sha'] == SUBJECT for x in [out, handoff, findings, verification])
for row in out['files']:
    b = blob(REVIEW, R + row['path'])
    assert len(b) == row['bytes'] and hashlib.sha256(b).hexdigest() == row['sha256']
for row in inputs:
    b = blob(row['commit'], row['path'])
    assert len(b) == row['bytes'] and hashlib.sha256(b).hexdigest() == row['sha256']
assert handoff['verdict'] == findings['verdict'] == 'APPROVE_SCOPED'
assert not findings['blocking_findings'] and not verification['failed']
old = [r for r in rows('service_observations.csv') if r['observation_id'] == 'OLD144']
assert len(old) == 1 and old[0]['raw_sha256'] == '' and old[0]['snapshot_sha256']
assert old[0]['date'] == '2026-12-13' and old[0]['route'] == 'KUF-SVX'
assert any(x['observation_id'] == 'OLD144' for x in findings['observations'])
sample = [r for r in rows('alternative_timing_examples.csv') if r['path'] == 'KUF>SVX>OMS'][0]
tz = {'KUF': 'Europe/Samara', 'SVX': 'Asia/Yekaterinburg', 'OMS': 'Asia/Omsk'}
def utc(date, clock, city):
    next_day = clock.endswith(' (+1)')
    clock = clock.removesuffix(' (+1)')
    local = datetime.fromisoformat(date + 'T' + clock) + timedelta(days=int(next_day))
    return local.replace(tzinfo=ZoneInfo(tz[city])).astimezone(ZoneInfo('UTC'))
departure = utc(sample['leg1_date'], sample['leg1_departure_local'], 'KUF')
arrival = utc(sample['leg2_date'], sample['leg2_arrival_local'], 'OMS')
elapsed = (arrival - departure).total_seconds() / 60
assert elapsed == float(sample['elapsed_min_minutes']) == 475
times = obj(REVIEW, R + 'probes/timing.json')
assert [x for x in times if x['path'] == sample['path']][0]['elapsed_minutes'] == elapsed
result = {
    'review_sha': REVIEW, 'subject_sha': SUBJECT,
    'status': 'APPROVE_SCOPED_RECEIPT_ADMITTED',
    'checks': {'review_output_hashes': len(out['files']), 'pinned_input_hashes': len(inputs),
               'historical_missing_hash_retained': 'OLD144', 'timezone_example_minutes': elapsed},
    'qualification': 'OLD144 historical primary bytes unavailable; a new publication is separate corroboration, not a replacement historical hash',
    'accepted_scope': 'Exact source claims and provenance with recorded limitations',
    'not_accepted': ['market coverage', 'bookability or residual seats', 'future subsidy awards',
                     'free fleet', 'downstream economics', 'full budget or final strategy'],
    'review_reexecuted_by_root': False,
}
Path(__file__).with_name('evidence_review_checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False))
