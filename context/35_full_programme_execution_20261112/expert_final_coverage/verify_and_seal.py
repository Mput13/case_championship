#!/usr/bin/env python3
"""Validate local review outputs and seal the bounded handoff. No source writes."""
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import subprocess
from collections import Counter

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]

def digest(b):
    return hashlib.sha256(b).hexdigest()

def readj(p):
    return json.loads(p.read_text())

def writej(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

checks = []
def check(name, condition, evidence):
    assert condition, name
    checks.append({'check': name, 'status': 'PASS', 'evidence': evidence})

coverage = list(csv.DictReader((OUT / 'coverage.csv').open()))
check('42_unique_atomic_claims', len(coverage) == 42 and len({r['expert_claim_id'] for r in coverage}) == 42, 'coverage.csv')
allowed = {'COVERED', 'PARTIAL', 'NOT_MODELLED', 'UNKNOWN', 'OUTSIDE_APPLICABILITY'}
check('status_vocabulary', all(r['status'] in allowed for r in coverage), sorted(allowed))
check('rows_have_scope_and_decision', all(r['rw_applicability'] and r['decision_changed'] and r['final_action'] and r['asr_confidence'] for r in coverage), 'All rows')
inputs = readj(OUT / 'input_manifest.json')
pinfiles = {r['path']: r for r in inputs['files']}
refs = set()
for r in coverage:
    for field in ['source_file_line_fragment', 'existing_exact_evidence']:
        for item in r[field].split('; '):
            if not item.startswith('context/'):
                continue
            path = re.split(r'[:#]', item, maxsplit=1)[0]
            check('existing_reference:' + path, (REPO / path).is_file(), r['expert_claim_id'])
            refs.add(path)
            m = re.search(r':(\d+)(?:-(\d+))?', item)
            if m:
                commit = pinfiles[path]['commit'] if path in pinfiles else inputs['project_commit']
                n = len(subprocess.check_output(['git', 'show', commit + ':' + path], cwd=REPO).decode().splitlines())
                check('reference_line_in_range:' + r['expert_claim_id'] + ':' + item, 1 <= int(m[1]) <= int(m[2] or m[1]) <= n, n)
check('all_cited_inputs_pinned', refs <= set(pinfiles), sorted(refs - set(pinfiles)))
for path, r in pinfiles.items():
    data = subprocess.check_output(['git', 'show', r['commit'] + ':' + path], cwd=REPO)
    check('immutable_input_verified:' + path, digest(data) == r['sha256'], r['commit'])
state = readj(OUT / 'observed_state.json')
check('expert_lines_116_73', sorted(state['expert_line_counts'].values()) == [73, 116], state['expert_line_counts'])
check('no_literal_mail', not any(state['literal_mail_matches'].values()), state['literal_mail_matches'])
check('no_literal_speed_fuel', not any(state['literal_speed_fuel_matches'].values()), state['literal_speed_fuel_matches'])
check('mail_source_is_user_context', coverage[40]['source_kind'] == 'USER_CONTEXT' and coverage[40]['status'] == 'UNKNOWN', coverage[40]['expert_claim_id'])
check('P15_quantitative_gap_real', state['P15']['evaluations_count'] == 0 and state['P15']['programmes_count'] == 0 and state['P15']['strategy'] is None, state['P15'])
assumptions = readj(OUT / 'assumptions.json')
check('unique_new_assumption_ids', len(assumptions) == 8 and len({r['assumption_id'] for r in assumptions}) == 8, [r['assumption_id'] for r in assumptions])
thresholds = list(csv.DictReader((OUT / 'decision_thresholds.csv').open()))
vg = {r['scenario']: r for r in thresholds if r['programme_id'] == 'VOG_RADIAL'}
for r in thresholds:
    expected = float(r['H_vs_KEEP_RUB']) - float(vg[r['scenario']]['H_vs_KEEP_RUB'])
    check('pairwise_arithmetic:' + r['programme_id'] + ':' + r['scenario'], math.isclose(float(r['H_vs_VOG_RADIAL_RUB']), expected, abs_tol=1e-7), expected)
check('VOG_cautious_exact_headroom', vg['cautious']['H_vs_KEEP_RUB'] == '263891478.0220616', vg['cautious'])
check('base_coefficient_ratio', math.isclose((math.log(2)/120)/(math.log(2)/3000), 25), 'P05-A07 algebra')
check('cautious_coefficient_ratio', math.isclose((math.log(2)/240)/(math.log(2)/1500), 6.25), 'P05-A07 algebra')
diag = readj(OUT / 'calendar_diagnostics.json')
check('reserve_no_commercial_assignments', all(r['reserve_N1_assigned_legs'] == 0 for r in diag), diag)
counts = dict(Counter(r['status'] for r in coverage))
writej('validation.json', {'status': 'PASS_BOUNDED_SOURCE_AND_ARTIFACT_CHECKS', 'check_count': len(checks), 'checks': checks,
                           'not_run': ['T01-T05 model replay', 'full canonical gzip model audit', 'browser or visual QA', 'market/dispatch/financial acceptance', 'web/live calls'],
                           'coverage_counts': counts})
writej('handoff.json', {
    'package': 'expert_final_coverage', 'version': '1.0-20261112',
    'status': 'COMPLETE_BOUNDED_REVIEW_WITH_FINAL_CONDITIONAL_WORDING',
    'coverage_verdict': 'PARTIAL_COVERAGE_CONDITIONAL_DECISION_READY_WITH_SPECIFIED_LIMITS',
    'overall_market_approval': False, 'dispatch_approval': False, 'financial_approval': False,
    'source_project_commit': inputs['project_commit'], 'source_expert_commit': inputs['expert_commit'],
    'P09_manifest_sha256': inputs['expected_manifests']['P09/manifest.json'],
    'P15_manifest_sha256': inputs['expected_manifests']['P15/output_manifest.json'],
    'entrypoint': 'summary.md', 'coverage': 'coverage.csv', 'final_copy': 'final_insertions.md',
    'actions': 'action_specification.md', 'assumptions': 'assumptions.json',
    'counts': counts, 'claim_rows': len(coverage), 'input_files_verified': len(pinfiles),
    'material_gaps': ['G1 rotations', 'G2 hub ramp/local support', 'G3 outage/recovery', 'G4 slots/time/generalized trip cost', 'G5 dated events'],
    'delivery_gap': 'P15 evaluations and programmes empty; strategy null at the exact source pin. Conditional P09 projection already exists.',
    'decision': 'EFC-A08 proposes VOG_RADIAL as conditional cautious-headroom reference, preserving growth alternatives and the 8-12 pair case; not an accepted investment recommendation.',
    'done': ['Full reading/deduplication of both transcripts', str(len(pinfiles)) + ' pinned input files and all 87 P03/P04 pins checked', '42 atomic coverage rows', '18 canonical arithmetic thresholds', '55 existing scenario rows extracted', 'source/copy/action package'],
    'concurrent_worktree_changes_outside_review': [r['path'] for r in pinfiles.values() if not r['working_bytes_equal_pinned_blob']],
    'not_run': ['new T01-T05 model evaluations', 'browser/visual test', 'market/live acceptance'],
    'root_action': 'Consume final wording/coverage; correct conditional result handoff and exact P09-to-P15 binding. No request to user for missing internal data; no new indefinite research cycle.',
    'write_scope': str(OUT.relative_to(REPO)),
    'boundaries': {'children': 0, 'git_mutations': 0, 'foreign_file_writes': 0, 'web_calls': 0, 'paid_runs': 0, 'publications': 0, 'restarts': 0, 'external_communications': 0, 'authorised_root_delivery': True},
    'delivery_target': {'environmentId': 'd463a92a-a497-4213-aeb8-69f0a1470b87', 'threadId': '91bc9ad6-4e9f-4954-8714-1e4366064b78'},
    'reproduce': ['python3 context/35_full_programme_execution_20261112/expert_final_coverage/build_package.py', 'python3 context/35_full_programme_execution_20261112/expert_final_coverage/coverage_builder.py', 'python3 context/35_full_programme_execution_20261112/expert_final_coverage/verify_and_seal.py']
})
excluded = {'output_manifest.json', 'output_manifest.sha256'}
files = [{'path': p.name, 'sha256': digest(p.read_bytes()), 'bytes': p.stat().st_size} for p in sorted(OUT.iterdir()) if p.is_file() and p.name not in excluded]
writej('output_manifest.json', {'package': 'expert_final_coverage', 'version': '1.0-20261112', 'status': 'SEALED_BOUNDED_REVIEW', 'path_base': str(OUT.relative_to(REPO)), 'file_count': len(files), 'files': files, 'hash_algorithm': 'SHA256 raw bytes', 'excluded': sorted(excluded), 'handoff': 'handoff.json', 'inputs': 'input_manifest.json'})
manifest_hash = digest((OUT / 'output_manifest.json').read_bytes())
(OUT / 'output_manifest.sha256').write_text(manifest_hash + '  output_manifest.json\n')
print(json.dumps({'checks': len(checks), 'manifest_files': len(files), 'manifest_sha256': manifest_hash, 'status': 'PASS_BOUNDED_REVIEW'}))
