#!/usr/bin/env python3
"""Pin two scoped review receipts and make the minimal D03 prose projection."""
import hashlib, json, math, subprocess
from functools import lru_cache
from pathlib import Path
BASE = 'context/28_evening_run_20261110/'
@lru_cache(maxsize=None)
def blob(s, p): return subprocess.check_output(['git', 'show', s + ':' + p])
def obj(s, p): return json.loads(blob(s, p))
packages = [
    ('network_review', 'cccc728b401d3a1234045220f42496ac48e0d475', 'b47118a48b6d5480217077bf8699a63665c0eb7a', 'review_manifest.json', 'subject_manifest.json'),
    ('digital_growth_review', '10464979fd510380aafe7e421d241a8f176d538d', 'd48b4a4f86de29aa968665f1601b785bd1824c54', 'output_manifest.json', 'source_manifest.json'),
]
results = []
for folder, review, subject, om, sm in packages:
    root = BASE + folder + '/'
    out, source = obj(review, root + om), obj(review, root + sm)
    handoff, findings = obj(review, root + 'handoff.json'), obj(review, root + 'findings.json')
    for x in [out, source, handoff, findings]: assert x.get('subjectSHA', x.get('subject_sha')) == subject
    assert handoff['verdict'] == findings['verdict'] == 'APPROVE_SCOPED' and not findings['blocking_findings']
    outputs = out.get('files', out.get('artifacts'))
    sources = source.get('files', source.get('subject_files'))
    for row in outputs:
        b = blob(review, root + row['path'])
        assert len(b) == row['bytes'] and hashlib.sha256(b).hexdigest() == row['sha256']
    for row in sources:
        b = blob(subject, row['path'])
        assert len(b) == row['bytes'] and hashlib.sha256(b).hexdigest() == row['sha256']
        assert subprocess.check_output(['git', 'rev-parse', subject + ':' + row['path']]).decode().strip() == row['git_blob']
    for row in source.get('pinned_inputs', []):
        b = blob(row['commit'], row['path'])
        assert len(b) == row['bytes'] and hashlib.sha256(b).hexdigest() == row['sha256']
    results.append({'role': folder, 'review_sha': review, 'subject_sha': subject,
                    'status': 'APPROVE_SCOPED_RECEIPT_ADMITTED',
                    'review_output_hashes': len(outputs), 'subject_blob_hashes_and_ids': len(sources),
                    'not_run': handoff['not_run'], 'review_reexecuted_by_root': False})

# A real source row from the independent simplex certificate, without rerunning the whole solver.
network = obj(packages[0][1], BASE + 'network_review/probes/results.json')
bank = next(r for r in network['details']['banks'] if r['network'] == 'KUF4' and r['scenario'] == 'base')
value = sum(q * p for q, p in zip(bank['solution'], bank['certificate']['upper_prices']))
assert math.isclose(value, bank['certificate']['primal'], abs_tol=1e-6)
assert math.isclose(value, bank['certificate']['dual'], abs_tol=1e-6)
results[0]['root_example'] = 'KUF4 independent local-product primal equals sum(quantity*unit margin) and dual'
results[0]['qualification'] = 'OMS4/OMS8 ideal-bank negative only under planning LF85/80; physical100 sensitivity and actual operation separate'

# D03 first-year contribution: prevented repeat contacts are a resource equivalent, not automatic cash.
digital = obj(packages[1][1], BASE + 'digital_growth_review/probes/arithmetic_checks.json')
sample = next(r for r in digital['checks'] if r['check'] == 'D03/base/first_year_result_after_implementation_rub')
assert math.isclose(60000 * .10 * 300 - 300000 - 700000, float(sample['actual']), abs_tol=1e-6)
results[1]['root_example'] = 'D03 60000 initial cases * .10 lower repeat probability *300 resource rubles -300000 support -700000 implementation'
results[1]['qualification'] = 'No measured effect, paid E2E, full budget or automatic cash saving; charter applicability remains UNKNOWN'
subject = packages[1][2]
path = BASE + 'digital_growth/cards.md'
original = blob(subject, path).decode()
old = 'регулярный прямой международный/иной рейс'
new = 'прямой международный/иной рейс'
assert original.count(old) == 1
corrected = original.replace(old, new)
assert corrected.replace(new, old, 1) == original
dest = Path(BASE) / 'integration/digital_growth'
dest.mkdir(parents=True, exist_ok=True)
(dest / 'cards.md').write_text(corrected)
correction = {'finding': 'EV-DIGITAL-N01', 'severity': 'P3', 'subject_sha': subject, 'source_path': path,
              'review_sha': packages[1][1], 'source_sha256': hashlib.sha256(original.encode()).hexdigest(),
              'projection_path': str(dest / 'cards.md'), 'projection_sha256': hashlib.sha256(corrected.encode()).hexdigest(),
              'change': {'from': old, 'to': new, 'occurrences': 1},
              'status': 'COORDINATOR_MINIMAL_PROSE_CORRECTION',
              'limits': ['Original exact review and owner files unchanged', 'No charter eligibility acceptance', 'No calculations changed'],
              'independent_correction_review': 'NOT_RUN; minimal wording fix only'}
(dest / 'correction.json').write_text(json.dumps(correction, ensure_ascii=False, indent=2) + '\n')
Path(__file__).with_name('network_digital_review_checks.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
print(json.dumps([{'role': r['role'], 'review_output_hashes': r['review_output_hashes'], 'subject_files': r['subject_blob_hashes_and_ids'], 'status': r['status']} for r in results], ensure_ascii=False))
