#!/usr/bin/env python3
"""Reproduce MR14's receipt bypass and this separate exact-input correction."""
import copy
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PREFIX = 'context/23_night_run_20261110/methods/'
SUBJECT = '7e65c687e12cf45534852a3c47d6a5c8cf7dda07'
ORACLE_COMMIT = 'ea2a9626aef75c121f2da7d778b47edce0d571b7'
RECEIPT = 'inputs/integration-oracle-001/receipt.json'
ORACLE = 'inputs/integration-oracle-001/independent_affected_itinerary.csv'
RECEIPT_SHA256 = '8373a8085682cc9df3660433f8024a78a377f9b512c93d05ecaafbc9a71d2db6'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def blob(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=REPO)


def save(name, value):
    (HERE/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    sources = []

    def exact(commit, path):
        data = blob(commit, path)
        record = dict(commit=commit, path=path, sha256=digest(data), bytes=len(data))
        if record not in sources:
            sources.append(record)
        return data

    original = exact(SUBJECT, PREFIX+'admit_frozen_interaction.py')
    corrected = (HERE/'admit_frozen_interaction.corrected.py').read_bytes()
    old = b"    receipt=json.loads((m.ROOT/'inputs/integration-oracle-001/receipt.json').read_text())"
    new = (b"    receipt_bytes=(m.ROOT/'inputs/integration-oracle-001/receipt.json').read_bytes()\n"
           b"    require(hashlib.sha256(receipt_bytes).hexdigest()=='8373a8085682cc9df3660433f8024a78a377f9b512c93d05ecaafbc9a71d2db6','ORACLE_RECEIPT_DRIFT_REQUIRES_NEW_REVIEW')\n"
           b"    receipt=json.loads(receipt_bytes)")
    assert original.count(old) == 1 and corrected == original.replace(old, new)
    receipt_bytes = exact(SUBJECT, PREFIX+RECEIPT)
    assert digest(receipt_bytes) == RECEIPT_SHA256
    receipt = json.loads(receipt_bytes)
    assert receipt['source_commit'] == ORACLE_COMMIT and len(receipt['files']) == 3
    oracle_sources = []
    for f in receipt['files']:
        data = exact(f['source_commit'], f['source_path'])
        owner_copy = exact(SUBJECT, PREFIX+f['path'])
        assert f['source_commit'] == ORACLE_COMMIT
        assert data == owner_copy and digest(data) == f['sha256'] and len(data) == f['bytes']
        oracle_sources.append(dict(source_path=f['source_path'], sha256=digest(data), bytes=len(data)))

    # Only the necessary pinned code and small inputs, in a disposable subtree.
    # git show still resolves the actual repository, not a mock or copied .git.
    with tempfile.TemporaryDirectory(prefix='.runtime-', dir=HERE) as temp:
        methods = Path(temp)/PREFIX
        methods.mkdir(parents=True)
        common_path = methods/'common_demand.py'
        common_path.write_bytes(exact(SUBJECT, PREFIX+'common_demand.py'))
        common = load('common_demand', common_path)
        guard_path = methods/'admit_frozen_interaction.py'
        guard_path.write_bytes(original)
        guard = load('guard_original', guard_path)
        protected = [guard.SALES, guard.SUMMARY, guard.FLIGHTS, guard.CAPACITY]
        inputs = protected+[RECEIPT]+[f['path'] for f in receipt['files']]
        baseline = {p: exact(SUBJECT, PREFIX+p) for p in inputs}

        def run(code, mutations):
            for path, data in baseline.items():
                q = methods/path
                q.parent.mkdir(parents=True, exist_ok=True)
                q.write_bytes(mutations.get(path, data))
            # compile each byte string afresh, no stale import/pyc.
            namespace = {'__name__': 'guard_replay', '__file__': str(guard_path)}
            exec(compile(code, str(guard_path), 'exec'), namespace)
            try:
                namespace['main']()
            except ValueError as error:
                return dict(status='REJECTED', reason=str(error)), {}
            outputs = {name: (methods/'runs/input_admission_v1'/name).read_bytes()
                       for name in ['checks.json', 'input_receipt.json', 'mutation_checks.json']}
            return dict(status='ACCEPTED'), outputs

        old_result, old_outputs = run(original, {})
        new_result, new_outputs = run(corrected, {})
        assert old_result == new_result == {'status': 'ACCEPTED'}
        replay_outputs = []
        for name, data in new_outputs.items():
            frozen = exact(SUBJECT, PREFIX+'runs/input_admission_v1/'+name)
            assert data == old_outputs[name] == frozen
            replay_outputs.append(dict(path=name, sha256=digest(data), bytes=len(data)))
        checks = json.loads(new_outputs['checks.json'])
        assert (checks['unique_itineraries'], checks['summary_groups'], checks['independent_affected_rows']) == (384, 12, 160)
        assert len(json.loads(new_outputs['mutation_checks.json'])) == 7

        def encoded(value):
            return (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()

        cases = []
        wrong_commit = copy.deepcopy(receipt)
        wrong_commit['source_commit'] = '0'*40
        cases.append(('wrong_source_commit', {RECEIPT: encoded(wrong_commit)}, 'ACCEPTED', 'ORACLE_RECEIPT_DRIFT_REQUIRES_NEW_REVIEW'))
        empty = copy.deepcopy(receipt)
        empty['files'] = []
        cases.append(('empty_file_list', {RECEIPT: encoded(empty)}, 'ACCEPTED', 'ORACLE_RECEIPT_DRIFT_REQUIRES_NEW_REVIEW'))
        changed = baseline[ORACLE]+b'\n'
        updated = copy.deepcopy(receipt)
        updated['files'][0]['sha256'] = digest(changed)
        updated['files'][0]['bytes'] = len(changed)
        cases.append(('changed_oracle_and_updated_receipt', {ORACLE: changed, RECEIPT: encoded(updated)}, 'ACCEPTED', 'ORACLE_RECEIPT_DRIFT_REQUIRES_NEW_REVIEW'))
        cases.append(('changed_oracle_and_empty_receipt', {ORACLE: changed, RECEIPT: encoded(empty)}, 'ACCEPTED', 'ORACLE_RECEIPT_DRIFT_REQUIRES_NEW_REVIEW'))
        cases.append(('oracle_change_without_receipt_change', {ORACLE: changed}, 'REJECTED', 'ORACLE_HASH_DRIFT'))
        for f in receipt['files'][1:]:
            cases.append(('changed_support_'+Path(f['path']).stem, {f['path']: baseline[f['path']]+b'\n'}, 'REJECTED', 'ORACLE_HASH_DRIFT'))
        for p in protected:
            cases.append(('changed_input_'+Path(p).name, {p: baseline[p]+b'\n'}, 'REJECTED', 'IMMUTABLE_HASH_DRIFT_REQUIRES_NEW_INPUT_SET_AND_ORACLE'))
        results = []
        for name, mutations, expected_old, expected_new_reason in cases:
            before, _ = run(original, mutations)
            after, _ = run(corrected, mutations)
            assert before['status'] == expected_old, (name, before)
            assert after == dict(status='REJECTED', reason=expected_new_reason), (name, after)
            results.append(dict(probe=name, original=before, corrected=after))

        example = list(csv.DictReader(io.StringIO(baseline[ORACLE].decode())))[0]
        assert abs(float(example['journeys'])*float(example['fare_once'])-float(example['lost_fare_once'])) < 1e-5
        save('validation.json', dict(status='PASS_PARENT_CORRECTION_CHECKS', original_subject=SUBJECT,
             independent_oracle_commit=ORACLE_COMMIT, receipt_sha256=RECEIPT_SHA256,
             unique_itineraries=384, summary_groups=12, affected_rows=160,
             exact_baseline_outputs=replay_outputs, original_seven_mutations_preserved=True,
             probes=results, grain_example=example, oracle_sources=oracle_sources,
             guard_change_only='receipt byte hash before parsing; calculations unchanged',
             independent_recheck='PENDING_NEW_TASK', old_interaction_automatically_protected=False,
             reusable_new_input_validator=False))
    save('source_manifest.json', dict(original_subject=SUBJECT, independent_oracle_commit=ORACLE_COMMIT,
                                    sources=sources))
    print(json.dumps(dict(status='PASS', input_git_hashes=len(sources), counterexamples=len(cases),
                          baseline_outputs_byte_identical=3, temporary_runtime_removed=True)))


if __name__ == '__main__':
    main()
