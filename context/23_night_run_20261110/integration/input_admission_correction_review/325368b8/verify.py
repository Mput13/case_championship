#!/usr/bin/env python3
"""Bounded MR15: exact Git inputs, real main before/after, scope-local runtime."""
import contextlib
import copy
import csv
import difflib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = '4a89bf1c04b24224a6a85a6cb9b6ca1cad032ab0'
OWNER = '7e65c687e12cf45534852a3c47d6a5c8cf7dda07'
MR14 = 'f579eeb888a98554b901afeee628c30a85cc48bf'
MR11 = 'ea2a9626aef75c121f2da7d778b47edce0d571b7'
FROZEN = 'f7a034dc91917cc69c5f8b3a729c3d1c6dfeb5b9'
NIGHT = 'context/23_night_run_20261110/'
METHODS = NIGHT + 'methods/'
CORRECTION = NIGHT + 'input_admission_correction/'
RECEIPT = 'inputs/integration-oracle-001/receipt.json'
ORACLE_NAMES = ['independent_affected_itinerary.csv', 'independent_cancellation16.csv',
                'adversarial_probes.json']
ORACLE = 'inputs/integration-oracle-001/' + ORACLE_NAMES[0]
PIN = '8373a8085682cc9df3660433f8024a78a377f9b512c93d05ecaafbc9a71d2db6'
PROTECTED = ['runs/common_demand_v1/itinerary_at_unit_scale.csv',
             'runs/common_demand_v1/summary.csv',
             'inputs/set001/tsiri_93fa/context/17_aircraft_route_review/model/flights.csv',
             'inputs/set001/tsiri_93fa/context/17_aircraft_route_review/model/capacity.csv']
OUTPUTS = ['checks.json', 'input_receipt.json', 'mutation_checks.json']
sources = {}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded(value))


def exact(commit, path, role='exact source evidence'):
    data = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=REPO)
    oid = subprocess.check_output(['git', 'rev-parse', commit + ':' + path], cwd=REPO,
                                  text=True).strip()
    key = (commit, path)
    if key not in sources:
        record = dict(commit=commit, path=path, git_blob=oid, sha256=digest(data),
                      bytes=len(data), roles=[], grain='document or exact source code')
        if path.endswith('.csv'):
            rows = table(data)
            record['grain'] = 'one CSV record; fields and row count retained'
            record['rows'] = len(rows)
            record['fields'] = list(rows[0]) if rows else []
        sources[key] = record
    if role not in sources[key]['roles']:
        sources[key]['roles'].append(role)
    return data


def table(data):
    return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))


def csv_bytes(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def main():
    for path in ['contract.md', 'briefs/input_admission_correction_review.md']:
        exact(ROOT, NIGHT + path, 'review contract')
    root_files = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', ROOT,
                                         CORRECTION], cwd=REPO, text=True).splitlines()
    root_data = {p[len(CORRECTION):]: exact(ROOT, p, 'review subject') for p in root_files}
    manifest = json.loads(root_data['output_manifest.json'])
    assert set(f['path'] for f in manifest['files']) == set(root_data) - {'output_manifest.json'}
    for f in manifest['files']:
        assert digest(root_data[f['path']]) == f['sha256']
        assert len(root_data[f['path']]) == f['bytes']
    claimed = json.loads(root_data['source_manifest.json'])
    for f in claimed['sources']:
        data = exact(f['commit'], f['path'], 'root claimed source independently checked')
        assert digest(data) == f['sha256'] and len(data) == f['bytes']

    prior = json.loads(exact(MR14, NIGHT + 'input_admission_review/findings.json',
                             'original finding; historical CHANGES retained'))
    assert prior['verdict'] == 'CHANGES'
    finding = next(f for f in prior['findings'] if f['id'] == 'MR14-P2-01')
    assert finding['severity'] == 'P2'
    suggested = exact(MR14, NIGHT + 'input_admission_review/suggested_fix.patch',
                      'independent MR14 minimal fix')
    original = exact(OWNER, METHODS + 'admit_frozen_interaction.py', 'original guard')
    corrected = root_data['admit_frozen_interaction.corrected.py']
    old_line = b"    receipt=json.loads((m.ROOT/'inputs/integration-oracle-001/receipt.json').read_text())"
    replacement = (b"    receipt_bytes=(m.ROOT/'inputs/integration-oracle-001/receipt.json').read_bytes()\n"
                   b"    require(hashlib.sha256(receipt_bytes).hexdigest()=='" + PIN.encode() +
                   b"','ORACLE_RECEIPT_DRIFT_REQUIRES_NEW_REVIEW')\n"
                   b"    receipt=json.loads(receipt_bytes)")
    assert original.count(old_line) == 1
    assert corrected == original.replace(old_line, replacement)
    delta = ''.join(difflib.unified_diff(original.decode().splitlines(True),
                                       corrected.decode().splitlines(True),
                                       fromfile='a/' + METHODS + 'admit_frozen_interaction.py',
                                       tofile='b/' + METHODS + 'admit_frozen_interaction.py'))
    assert delta.encode() == root_data['minimal_fix.patch'] == suggested
    (HERE / 'verified_minimal_diff.patch').write_text(delta)

    receipt_bytes = exact(OWNER, METHODS + RECEIPT, 'receipt pinned by corrected main')
    assert digest(receipt_bytes) == PIN
    receipt = json.loads(receipt_bytes)
    assert receipt['input_set_id'] == 'integration-oracle-001'
    assert receipt['source_commit'] == MR11
    assert len(receipt['files']) == 3
    by_name = {Path(f['path']).name: f for f in receipt['files']}
    assert set(by_name) == set(ORACLE_NAMES)
    oracle_checks = []
    baseline = {RECEIPT: receipt_bytes}
    for name in ORACLE_NAMES:
        f = by_name[name]
        assert f['source_commit'] == MR11
        assert f['source_path'] == NIGHT + 'methods_integration_review/' + name
        assert f['path'] == 'inputs/integration-oracle-001/' + name
        upstream = exact(MR11, f['source_path'], 'independent MR11 oracle')
        copied = exact(OWNER, METHODS + f['path'], 'owner imported oracle')
        assert upstream == copied
        assert digest(upstream) == f['sha256'] and len(upstream) == f['bytes']
        baseline[f['path']] = copied
        oracle_checks.append(dict(name=name, source_commit=MR11, source_path=f['source_path'],
                                  local_path=f['path'], sha256=digest(upstream),
                                  bytes=len(upstream), owner_equals_exact_MR11=True))
    for path in PROTECTED:
        baseline[path] = exact(OWNER, METHODS + path, 'protected input')
        assert baseline[path] == exact(FROZEN, METHODS + path, 'guard frozen comparison target')
    common = exact(OWNER, METHODS + 'common_demand.py', 'unchanged rows/save support')
    published = {name: exact(OWNER, METHODS + 'runs/input_admission_v1/' + name,
                             'published baseline output') for name in OUTPUTS}
    affected = table(baseline[ORACLE])
    assert len(affected) == 160
    assert len({tuple(r[k] for k in ['candidate', 'scenario', 'recipe', 'flight_ids'])
                for r in affected}) == 160
    cancellation = table(baseline['inputs/integration-oracle-001/' + ORACLE_NAMES[1]])
    adversarial = json.loads(baseline['inputs/integration-oracle-001/' + ORACLE_NAMES[2]])
    assert len(cancellation) == 16 and len(adversarial['probes']) == adversarial['count'] == 17
    assert next(p for p in adversarial['probes']
                if p['name'] == 'hypothetical_delay_money_never_accepted')['evidence']['held_rows'] == 4
    save('receipt_checks.json', dict(status='PASS', receipt_owner=OWNER, receipt_sha256=PIN,
         input_set_id=receipt['input_set_id'], source_commit=receipt['source_commit'],
         files=oracle_checks, coverage=dict(files=3, affected_unique_rows=160,
         cancellation_rows=16, adversarial_probes=17, upstream_delay_holds=4),
         source_manifest_entries_verified=len(claimed['sources']),
         root_output_manifest_entries_verified=len(manifest['files']),
         pin_established_from_exact_owner_not_local_receipt=True,
         exact_MR11_blobs_independently_compared=True))

    # Execute the subject's exact runner with only its output/runtime roots relocated.
    # No line of its algorithm or expected result is replaced.
    with tempfile.TemporaryDirectory(prefix='.runtime-parent-', dir=HERE) as temp:
        parent = Path(temp)
        runner_path = parent / 'verify_correction.py'
        runner_path.write_bytes(root_data['verify_correction.py'])
        (parent / 'admit_frozen_interaction.corrected.py').write_bytes(corrected)
        namespace = dict(__name__='relocated_parent_runner', __file__=str(runner_path))
        exec(compile(root_data['verify_correction.py'], str(runner_path), 'exec'), namespace)
        namespace['HERE'] = parent
        namespace['REPO'] = REPO
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            namespace['main']()
        for name in ['validation.json', 'source_manifest.json']:
            data = (parent / name).read_bytes()
            assert data == root_data[name]
            save('parent_replay/' + name, json.loads(data))
        save('parent_runner_replay.json', dict(status='PASS',
             exact_runner_sha256=digest(root_data['verify_correction.py']),
             relocation='HERE and REPO only; original bytes and algorithm unchanged',
             summary=json.loads(captured.getvalue()),
             regenerated_validation_byte_identical=True,
             regenerated_source_manifest_byte_identical=True))

    results = []
    cases = []
    drift = 'ORACLE_RECEIPT_DRIFT_REQUIRES_NEW_REVIEW'

    def case(name, mutations, old_reason=None, new_reason=drift, details=None):
        assert all(p in baseline for p in mutations)
        assert all(baseline[p] != data for p, data in mutations.items())
        cases.append((name, mutations, old_reason, new_reason, details or {}))

    changed = copy.deepcopy(receipt)
    changed['source_commit'] = '0' * 40
    case('receipt_wrong_source_commit', {RECEIPT: encoded(changed)})
    changed = copy.deepcopy(receipt)
    changed['files'] = []
    case('receipt_empty_coverage', {RECEIPT: encoded(changed)})
    changed = copy.deepcopy(receipt)
    changed['files'][0]['source_commit'] = '1' * 40
    changed['files'][0]['source_path'] = 'same_owner/not_independent.csv'
    case('receipt_wrong_per_file_provenance', {RECEIPT: encoded(changed)})
    case('receipt_formatting_only_exact_bytes_policy', {RECEIPT: receipt_bytes + b'\n'})

    def self_receipted(path, data):
        updated = copy.deepcopy(receipt)
        f = next(f for f in updated['files'] if f['path'] == path)
        f['sha256'] = digest(data)
        f['bytes'] = len(data)
        return {path: data, RECEIPT: encoded(updated)}

    changed_oracle = baseline[ORACLE] + b'\n'
    case('oracle_bytes_and_self_updated_receipt', self_receipted(ORACLE, changed_oracle))
    case('oracle_changed_and_receipt_empty',
         {ORACLE: changed_oracle, RECEIPT: encoded(dict(receipt, files=[]))})
    case('oracle_changed_receipt_unchanged', {ORACLE: changed_oracle},
         'ORACLE_HASH_DRIFT', 'ORACLE_HASH_DRIFT')

    # Independent substantive witness: rewrite the supporting cancellation evidence.
    support = 'inputs/integration-oracle-001/' + ORACLE_NAMES[1]
    forged_cancel = copy.deepcopy(cancellation)
    before_fields = {k: forged_cancel[0][k] for k in ['delta', 'full_budget', 'actual_cash']}
    forged_cancel[0].update(delta='123456789', full_budget='0', actual_cash='0')
    case('own_fabricated_cancellation_evidence_self_receipted',
         self_receipted(support, csv_bytes(forged_cancel)), details=dict(
         grain='first of 16 cancellation-policy records; affected oracle and protected inputs unchanged',
         original_fields=before_fields,
         substituted_fields={k: forged_cancel[0][k] for k in before_fields},
         purpose='Tests provenance of required support, not financial-model acceptance'))
    case('support_semantics_changed_receipt_unchanged', {support: csv_bytes(forged_cancel)},
         'ORACLE_HASH_DRIFT', 'ORACLE_HASH_DRIFT')

    # Keep list length three while removing two distinct mandatory support paths.
    coverage = copy.deepcopy(receipt)
    coverage['files'] = [copy.deepcopy(receipt['files'][0]) for _ in range(3)]
    case('own_three_entries_but_duplicate_coverage_and_forged_support',
         {RECEIPT: encoded(coverage), support: csv_bytes(forged_cancel)}, details=dict(
         listed_entries=3, distinct_paths=1, omitted_support_files=ORACLE_NAMES[1:],
         purpose='A length-only coverage check would miss omitted support'))

    # Same-input reconstruction preserves every checked value and full key coverage,
    # while explicitly removing the independent origin of the oracle.
    sales = table(baseline[PROTECTED[0]])
    sale_map = {(r['network'], r['scenario'], r['recipe'], r['flight_ids']): r for r in sales}
    reconstructed = []
    for r in reversed(affected):
        s = sale_map[tuple(r[k] for k in ['candidate', 'scenario', 'recipe', 'flight_ids'])]
        reconstructed.append(dict(candidate=r['candidate'], scenario=r['scenario'], recipe=r['recipe'],
             flight_ids=r['flight_ids'], affected_leg_count=r['affected_leg_count'],
             journeys=s['sold_journeys'], fare_once=s['fare_once'], lost_fare_once=s['gross_revenue'],
             reviewer_source='REBUILT_FROM_OWNER_SALES_NOT_MR11'))
    case('same_input_reconstruction_self_receipted',
         self_receipted(ORACLE, csv_bytes(reconstructed)), details=dict(
         rows=160, order='reversed', value_source='protected owner sales',
         new_column='reviewer_source=REBUILT_FROM_OWNER_SALES_NOT_MR11'))
    numeric = copy.deepcopy(affected)
    numeric[0]['journeys'] = str(float(numeric[0]['journeys']) + 1)
    case('oracle_numeric_disagreement_self_receipted', self_receipted(ORACLE, csv_bytes(numeric)),
         'INDEPENDENT_AFFECTED_ORACLE', drift,
         dict(purpose='Existing numerical comparison still rejects wrong quantities in original'))
    other_support = 'inputs/integration-oracle-001/' + ORACLE_NAMES[2]
    case('adversarial_support_changed_receipt_unchanged',
         {other_support: baseline[other_support] + b'\n'}, 'ORACLE_HASH_DRIFT', 'ORACLE_HASH_DRIFT')
    for path in PROTECTED:
        case('protected_input_' + Path(path).name, {path: baseline[path] + b'\n'},
             'IMMUTABLE_HASH_DRIFT_REQUIRES_NEW_INPUT_SET_AND_ORACLE',
             'IMMUTABLE_HASH_DRIFT_REQUIRES_NEW_INPUT_SET_AND_ORACLE')

    with tempfile.TemporaryDirectory(prefix='.runtime-own-', dir=HERE) as temp:
        methods = Path(temp) / METHODS
        methods.mkdir(parents=True)
        (methods / 'common_demand.py').write_bytes(common)
        guard_path = methods / 'admit_frozen_interaction.py'
        output_dir = methods / 'runs/input_admission_v1'

        def run(code, mutations, expected_reason):
            for path, data in baseline.items():
                target = methods / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(mutations.get(path, data))
            if output_dir.exists():
                shutil.rmtree(output_dir)
            guard_path.write_bytes(code)
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
            proc = subprocess.run([sys.executable, '-B', str(guard_path)], cwd=methods,
                                  env=env, capture_output=True, text=True, timeout=30)
            emitted = {p.name: p.read_bytes() for p in output_dir.glob('*')} if output_dir.exists() else {}
            reason = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else None
            if expected_reason is None:
                assert proc.returncode == 0 and reason is None, (proc.returncode, proc.stderr)
                assert set(emitted) == set(OUTPUTS)
                assert emitted == published
            else:
                assert proc.returncode != 0 and reason == 'ValueError: ' + expected_reason, proc.stderr
                assert not emitted, 'Rejected main emitted admission outputs'
            return dict(status='ACCEPTED' if proc.returncode == 0 else 'REJECTED',
                        exit_code=proc.returncode, error=reason,
                        output_files=len(emitted),
                        outputs_equal_published=(emitted == published) if emitted else None), emitted

        original_baseline, before = run(original, {}, None)
        corrected_baseline, after = run(corrected, {}, None)
        assert before == after == published
        for name, data in after.items():
            (HERE / 'baseline').mkdir(exist_ok=True)
            (HERE / 'baseline' / name).write_bytes(data)
        for name, mutations, old_reason, new_reason, details in cases:
            old, _ = run(original, mutations, old_reason)
            new, _ = run(corrected, mutations, new_reason)
            results.append(dict(probe=name, details=details,
                 mutated_inputs=[dict(path=p, baseline_sha256=digest(baseline[p]),
                                      mutant_sha256=digest(data), bytes=len(data))
                                 for p, data in sorted(mutations.items())],
                 original=old, corrected=new))

    assert not list(HERE.glob('.runtime-*'))
    summary = json.loads(published['checks.json'])
    assert (summary['unique_itineraries'], summary['summary_groups'],
            summary['independent_affected_rows']) == (384, 12, 160)
    assert len(json.loads(published['mutation_checks.json'])) == 7
    save('own_probes.json', dict(status='PASS_EXPECTATIONS', cases=len(results),
         original_bypasses=sum(r['original']['status'] == 'ACCEPTED' for r in results),
         corrected_rejections=sum(r['corrected']['status'] == 'REJECTED' for r in results),
         probes=results))
    save('checks.json', dict(status='PASS_BOUNDED_MR15_CHECKS', subject_commit=ROOT,
         original_subject=OWNER, original_review=MR14, independent_oracle=MR11,
         source_files=len(sources), parent_runner_reproduced=True,
         parent_counterexamples=11, own_main_cases=len(results),
         own_original_bypasses=sum(r['original']['status'] == 'ACCEPTED' for r in results),
         own_corrected_rejections=len(results), baseline_original=original_baseline,
         baseline_corrected=corrected_baseline,
         baseline_outputs=[dict(path=n, sha256=digest(published[n]), bytes=len(published[n])) for n in OUTPUTS],
         unique_itineraries=384, summary_groups=12, independent_affected_rows=160,
         seven_owner_mutations_byte_preserved=True,
         change_exactly_matches_MR14_suggested_patch=True,
         root_manifests_verified=True, receipt_and_three_exact_MR11_blobs_verified=True,
         fresh_process_main=True, rejected_main_emits_no_outputs=True,
         temporary_runtime_removed=True, original_MR14_verdict='CHANGES',
         old_interaction_automatically_protected=False, new_inputs_accepted=False,
         full_MR11_MR12_MR13_passport_repeated=False))
    save('source_manifest.json', dict(review_id='MR15', subject_commit=ROOT,
         original_owner=OWNER, original_review=MR14, independent_oracle=MR11,
         input_policy='git show exact-commit:path only; no worktree input bytes',
         sources=[sources[k] for k in sorted(sources)]))
    print(json.dumps(dict(status='PASS', own_main_cases=len(results),
                         original_bypasses=sum(r['original']['status'] == 'ACCEPTED' for r in results),
                         corrected_rejections=len(results), baseline_identical=3,
                         source_blobs=len(sources), runtime_removed=True)))


if __name__ == '__main__':
    main()
