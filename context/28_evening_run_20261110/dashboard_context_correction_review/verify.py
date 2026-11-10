#!/usr/bin/env python3
"""Bounded independent ROOT-DASH-01 recheck of exact frozen Git objects.

Default is read-only. --record writes reviewer evidence only beside this file.
No imports from the owner builder are used for the independent reconstruction.
The separately labelled owner replay executes inspected exact code in memory.
"""
import argparse
import collections
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
REPO = Path(subprocess.check_output(['git', '-C', str(HERE), 'rev-parse', '--show-toplevel'], text=True).strip())
ROOT = '0f07ec43ad3cf515e3bafbb767ade9caa2ba984c'
ORIGINAL = '5101302f93c349268f4ba0ff26832ff261e1a9e7'
EVIDENCE = '38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b'
BASE = 'context/28_evening_run_20261110/'
OLD = BASE + 'dashboard_handoff/'
FIX = BASE + 'integration/dashboard_context_correction/'
RETAINED = BASE + 'integration/dashboard_handoff/5101302f/'
GAP = 'RC:calculation_pair_gap:PC:network:route_delta:254'
ASSOCIATION = 'CALCULATION_LEG_CONTEXT:C33:KUF-SVX'
SOURCES = {}


def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args])


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def blob(commit, path):
    data = git('show', commit + ':' + path)
    SOURCES[(commit, path)] = dict(commit=commit, path=path, bytes=len(data),
        sha256=sha256(data), git_blob=git('rev-parse', commit + ':' + path).decode().strip())
    return data


def obj(commit, path):
    return json.loads(blob(commit, path))


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def table(commit, path):
    return list(csv.DictReader(io.StringIO(blob(commit, path).decode())))


def unique(rows):
    ids = [r['record_id'] for r in rows]
    assert len(ids) == len(set(ids)), 'duplicate context record_id'


def source_key(row):
    p = row['provenance']
    return p['commit'], p['path'], p['source_row']


def leaves(value, path=''):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from leaves(v, path + '/' + k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from leaves(v, path + '/' + str(i))
    else:
        yield path, value


def main(record=False):
    before_files = {p.name: sha256(p.read_bytes()) for p in (REPO / FIX).iterdir() if p.is_file()}
    original = obj(ORIGINAL, OLD + 'route_context.json')
    cards = obj(ORIGINAL, OLD + 'cards.json')
    program = obj(ORIGINAL, OLD + 'program_changes.json')
    fixed = obj(ROOT, FIX + 'route_context.json')
    fixed_cards = obj(ROOT, FIX + 'cards.json')
    patch = obj(ROOT, FIX + 'context_patch.json')
    readme = blob(ROOT, FIX + 'README.md').decode()
    registry_rows = table(EVIDENCE, BASE + 'evidence/pair_registry.csv')
    registry = {r['route']: r for r in registry_rows}
    joins = table(EVIDENCE, BASE + 'evidence/pair_hypothesis_join.csv')
    links = table(ORIGINAL, OLD + 'route_links.csv')
    assert len(registry) == len(registry_rows) == 45
    assert len(joins) == len(links) == 85
    assert [{k: v for k, v in r.items() if k != 'provenance'} for r in links] == joins
    assert registry['KUF-SVX']['hypotheses'] == 'C03'
    assert [(r['hypothesis'], r['route']) for r in joins if r['route'] == 'KUF-SVX'] == [('C03', 'KUF-SVX')]
    assert registry_rows[19]['route'] == 'KUF-SVX'  # logical CSV record 21
    assert {'TLV-ZIA', 'SVX-ZIA'}.isdisjoint(registry)
    unique(original['rows'])
    unique(fixed['rows'])
    originals = {r['record_id']: r for r in original['rows']}
    false_gap = originals[GAP]
    assert false_gap['hypothesis_id'] == 'C33' and false_gap['route'] == 'KUF-SVX'
    assert false_gap['coverage_status'] == 'NOT_IN_EVIDENCE_PAIR_REGISTRY'
    supporting = [r for r in original['rows'] if r['hypothesis_id'] == 'C03' and r['route'] == 'KUF-SVX']
    legs = [r for r in program['rows'] if r['hypothesis_id'] == 'C33' and r['route'] == 'KUF-SVX']
    assert len(supporting) == 34 and len(legs) == 16
    assert not [r for r in original['rows'] if r['hypothesis_id'] == 'C33' and r['route'] == 'KUF-SVX' and r['record_type'] != 'calculation_pair_gap']

    # All 34 supporting records are anchored independently in evidence38f CSVs.
    kinds = {'pair_coverage': 'pair_registry', 'weekly_service_summary': 'weekly_service_context',
             'published_departure': 'dated_service_instances', 'fare': 'fare_observations', 'gap': 'decision_gaps'}
    evidence_tables = {kind: table(EVIDENCE, BASE + 'evidence/' + name + '.csv') for kind, name in kinds.items()}
    source_checks = []
    for r in supporting:
        p = r['provenance']
        path = BASE + 'evidence/' + kinds[r['record_type']] + '.csv'
        assert p['commit'] == EVIDENCE and p['path'] == path
        raw = blob(EVIDENCE, path)
        assert p['sha256'] == sha256(raw)
        assert p['git_blob'] == SOURCES[(EVIDENCE, path)]['git_blob']
        assert p['locator_kind'] == 'csv_record_including_header'
        assert p['source_id'] == 'S' + sha256((EVIDENCE + ':' + path).encode())[:16]
        assert p['url'] == 'https://github.com/Mput13/case_championship/blob/' + EVIDENCE + '/' + path
        raw_row = evidence_tables[r['record_type']][p['source_row'] - 2]
        assert r['source_fields'] == raw_row and raw_row['route'] == 'KUF-SVX'
        assert r['origin'] == raw_row.get('origin', raw_row.get('airport_a', ''))
        assert r['destination'] == raw_row.get('destination', raw_row.get('airport_b', ''))
        assert r['date'] == raw_row.get('date', '')
        assert r['period_start'] == raw_row.get('period_start', '')
        assert r['period_end'] == raw_row.get('period_end', '')
        assert r['frequency_value'] == raw_row.get('oneway_departures', '')
        assert r['price_value'] == raw_row.get('advertised_from_rub', '')
        assert r['complete_market'] == 'False'
        source_checks.append(dict(record_id=r['record_id'], record_type=r['record_type'],
            source_path=path, source_row=p['source_row'], source_fields_sha256=sha256(encode(raw_row))))

    # Validate the 16 concrete calculation-leg locators, without rerunning a solver.
    programme_checks = []
    for r in legs:
        p = r['provenance']
        assert p['commit'] == 'b47118a48b6d5480217077bf8699a63665c0eb7a'
        assert p['path'] in {BASE + 'network/v2/outputs/route_deltas.csv', BASE + 'network/v2/outputs/dated_flights.csv'}
        data = blob(p['commit'], p['path'])
        assert p['sha256'] == sha256(data) and p['git_blob'] == SOURCES[(p['commit'], p['path'])]['git_blob']
        raw_row = list(csv.DictReader(io.StringIO(data.decode())))[p['source_row'] - 2]
        assert raw_row == r['source_fields']
        assert r['origin'] == raw_row['origin'] and r['destination'] == raw_row['destination']
        assert '-'.join(sorted([r['origin'], r['destination']])) == 'KUF-SVX'
        assert r['directed_route'] == r['origin'] + '-' + r['destination']
        programme_checks.append(dict(record_id=r['record_id'], record_type=r['record_type'],
            directed_route=r['directed_route'], provenance=p, source_fields_sha256=sha256(encode(raw_row))))

    # The expected correction is the single fixed case, constructed independently.
    aliases = []
    for r in supporting:
        alias = copy.deepcopy(r)
        alias.update(record_id='RC:calculation_link:C33:' + r['record_id'], hypothesis_id='C33',
            association_id=ASSOCIATION, original_evidence_record_id=r['record_id'],
            association_kind='DERIVED_CALCULATION_LEG_LINK_NOT_NEW_OBSERVATION')
        aliases.append(alias)
    expected_context = copy.deepcopy(original)
    expected_context['rows'] = [r for r in original['rows'] if r['record_id'] != GAP] + aliases
    expected_context['association_boundary'] = 'Added aliases link existing evidence to calculation legs; deduplicate observations by original_evidence_record_id or exact source locator, never sum cross-hypothesis aliases.'
    expected_cards = copy.deepcopy(cards)
    c33 = next(c for c in expected_cards['cards'] if c['hypothesis_id'] == 'C33')
    c33['route_context_ids'] = [i for i in c33['route_context_ids'] if i != GAP] + [r['record_id'] for r in aliases]
    assert encode(expected_context) == blob(ROOT, FIX + 'route_context.json')
    assert encode(expected_cards) == blob(ROOT, FIX + 'cards.json')
    expected_association = dict(association_id=ASSOCIATION, hypothesis_id='C33', route='KUF-SVX',
        basis='CALCULATION_LEG_EXACT_AIRPORT_PAIR', registry_hypotheses='C03',
        programme_record_ids=[r['record_id'] for r in legs], programme_source_refs=[r['provenance'] for r in legs],
        original_evidence_record_ids=[r['record_id'] for r in supporting], no_new_observations=True,
        no_automatic_future_extension=True)
    assert patch == dict(subject_sha=ORIGINAL, evidence_sha=EVIDENCE, finding='ROOT-DASH-01',
        removed_context_record_ids=[GAP], added_context_record_ids=[r['record_id'] for r in aliases],
        associations=[expected_association], original_85_route_links_unchanged=True,
        review_status='ROOT_CORRECTION_PENDING_INDEPENDENT_RECHECK',
        scope='Only context associations; no prices, frequencies, economic calculations or source acceptance changed')

    fixed_ids = {r['record_id']: r for r in fixed['rows']}
    for card in fixed_cards['cards']:
        ids = card['route_context_ids']
        assert len(ids) == len(set(ids))
        assert all(i in fixed_ids and fixed_ids[i]['hypothesis_id'] == card['hypothesis_id'] for i in ids)
        assert set(ids) == {r['record_id'] for r in fixed['rows'] if r['hypothesis_id'] == card['hypothesis_id']}
    assert GAP not in json.dumps(fixed) and GAP not in json.dumps(fixed_cards)
    assert not [r for r in fixed['rows'] if r['hypothesis_id'] == 'C33' and
                (r['record_type'] == 'calculation_pair_gap' or r['coverage_status'] == 'NOT_IN_EVIDENCE_PAIR_REGISTRY')]
    actual_gaps = [r for r in fixed['rows'] if r['record_type'] == 'calculation_pair_gap']
    assert {r['route'] for r in actual_gaps} == {'TLV-ZIA', 'SVX-ZIA'}
    assert all(r == originals[r['record_id']] for r in actual_gaps)
    assert all(r['route'] not in registry for r in actual_gaps)
    card_checks = []
    for old, new in zip(cards['cards'], fixed_cards['cards']):
        assert old['hypothesis_id'] == new['hypothesis_id']
        changed = [k for k in old if old[k] != new[k]]
        assert changed == (['route_context_ids'] if old['hypothesis_id'] == 'C33' else [])
        assert old['metrics'] == new['metrics']
        card_checks.append(dict(hypothesis_id=old['hypothesis_id'], metrics=len(old['metrics']),
            metric_set_sha256=sha256(encode(old['metrics'])), changed_keys=changed,
            old_context_refs=len(old['route_context_ids']), new_context_refs=len(new['route_context_ids'])))
    assert sum(x['metrics'] for x in card_checks) == 164
    assert {k: v for k, v in cards.items() if k != 'cards'} == {k: v for k, v in fixed_cards.items() if k != 'cards'}
    numeric_cells = []
    for r in aliases:
        source = originals[r['original_evidence_record_id']]
        for path, value in leaves(r):
            if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '', 1).replace('-', '', 1).isdigit()):
                numeric_cells.append(dict(record_id=r['record_id'], pointer=path, value=value))
        assert {k: v for k, v in r.items() if k not in {'record_id', 'hypothesis_id', 'association_id', 'original_evidence_record_id', 'association_kind'}} == {k: v for k, v in source.items() if k not in {'record_id', 'hypothesis_id'}}

    # Original package retained byte-for-byte, including its legacy CSV and links.
    tree = git('ls-tree', '-r', ORIGINAL, OLD).decode().splitlines()
    retained = []
    for entry in tree:
        meta, path = entry.split('\t', 1)
        target = RETAINED + path[len(OLD):]
        original_blob = meta.split()[2]
        assert git('rev-parse', ROOT + ':' + target).decode().strip() == original_blob
        retained.append(dict(original_path=path, retained_path=target, git_blob=original_blob))

    owner_sources = obj(ROOT, FIX + 'source_manifest.json')
    expected_sources = [(ORIGINAL, OLD + n) for n in ['route_context.json', 'cards.json', 'program_changes.json', 'route_links.csv']]
    expected_sources.append((EVIDENCE, BASE + 'evidence/pair_registry.csv'))
    assert [(r['commit'], r['path']) for r in owner_sources] == expected_sources
    for r in owner_sources:
        data = blob(r['commit'], r['path'])
        assert r == SOURCES[(r['commit'], r['path'])]
    owner_outputs = obj(ROOT, FIX + 'output_manifest.json')
    assert [r['path'] for r in owner_outputs] == ['cards.json', 'checks.json', 'context_patch.json', 'route_context.json', 'source_manifest.json']
    for r in owner_outputs:
        data = blob(ROOT, FIX + r['path'])
        assert sha256(data) == r['sha256'] and len(data) == r['bytes']
    assert 'cards.json и route_context.json из этой папки' in readme
    assert 'остальные файлы' in readme and '../dashboard_handoff/5101302f/README.md' in readme
    assert 'Исходные 85 связей' in readme and 'context_patch.json' in readme
    assert 'исключать дубли' in readme and 'UI Насти не выполнялось' in readme
    assert 'Исходный CHANGES не заменяется' in readme

    # Counterexamples are restricted to this frozen defect and its actual records.
    probes = []
    def no_false_registry_absence(rows):
        assert not [r for r in rows if r['coverage_status'] == 'NOT_IN_EVIDENCE_PAIR_REGISTRY' and r['route'] in registry]
    try:
        no_false_registry_absence(original['rows'])
    except AssertionError:
        probes.append(dict(id='missing_association_is_not_global_absence', status='PASS',
            original_rejected=True, original_gap=GAP, registry_csv_record=21, registry_hypotheses='C03'))
    else:
        raise AssertionError('original false absence not detected')
    no_false_registry_absence(fixed['rows'])
    probes.append(dict(id='true_registry_gaps_preserved', status='PASS', routes=['TLV-ZIA', 'SVX-ZIA'],
        source_records_unchanged=True, not_evidence_of_no_flights=True))

    # Owner code is used only for its separately identified negative/idempotence replay.
    build_path = FIX + 'build.py'
    namespace = {'__file__': str(REPO / build_path), '__name__': 'reviewer_owner_replay'}
    exec(compile(blob(ROOT, build_path), ROOT + ':' + build_path, 'exec'), namespace)
    for label, rows in [('original_record', original), ('new_alias_record', fixed)]:
        duplicate = copy.deepcopy(rows)
        duplicate['rows'].append(copy.deepcopy(rows['rows'][-1]))
        try:
            namespace['project'](duplicate, cards if label == 'original_record' else fixed_cards, program, registry)
        except AssertionError:
            probes.append(dict(id='duplicate_' + label + '_rejected_by_owner', status='PASS'))
        else:
            raise AssertionError('duplicate ID accepted')
        try:
            unique(duplicate['rows'])
        except AssertionError:
            pass
        else:
            raise AssertionError('independent duplicate check accepted duplicate')
    again, again_cards, again_patch = namespace['project'](fixed, fixed_cards, program, registry)
    assert again == fixed and again_cards == fixed_cards and not again_patch['associations']
    probes.append(dict(id='reapply_has_no_growth', status='PASS', context_rows=672, new_associations=0))
    absent_support = copy.deepcopy(original)
    absent_support['rows'] = [r for r in original['rows'] if r not in supporting]
    try:
        namespace['project'](absent_support, cards, program, registry)
    except AssertionError as exc:
        assert 'Known registry route without delivered context' in str(exc)
        probes.append(dict(id='known_route_missing_delivered_support_refused', status='PASS', message=str(exc)))
    else:
        raise AssertionError('unsupported known-route association was invented')
    old_departures = [r for r in original['rows'] if r['record_type'] == 'published_departure']
    new_departures = [r for r in fixed['rows'] if r['record_type'] == 'published_departure']
    assert {source_key(r) for r in old_departures} == {source_key(r) for r in new_departures}
    assert len({source_key(r) for r in new_departures}) == 215
    pair_departures = [r for r in new_departures if r['route'] == 'KUF-SVX']
    assert len(pair_departures) == 52 and len({source_key(r) for r in pair_departures}) == 26
    pair_canonical = {r.get('original_evidence_record_id', r['record_id']) for r in fixed['rows'] if r['route'] == 'KUF-SVX'}
    assert len(pair_canonical) == 34
    old_evidence = [r for r in original['rows'] if r['record_type'] != 'calculation_pair_gap']
    new_evidence = [r for r in fixed['rows'] if r['record_type'] != 'calculation_pair_gap']
    assert {source_key(r) for r in old_evidence} == {source_key(r) for r in new_evidence}
    probes.append(dict(id='cross_hypothesis_alias_sum_counterexample', status='PASS',
        naive_KUF_SVX_departure_rows=52, unique_source_departures=26,
        naive_KUF_SVX_context_rows=68, original_record_ids=34,
        all_unique_published_departures_before=215, all_unique_published_departures_after=215,
        interpretation='Record IDs are unique associations; count observations once by original ID or exact source locator. Do not sum summaries, coverage counts and departures.'))
    dated = obj(EVIDENCE, BASE + 'evidence/dated_checks.json')
    assert (dated['expanded_records'], dated['unique_instances'], dated['duplicates_collapsed'], dated['conflicting_instances']) == (359, 215, 144, 12)

    # --verify is executed from the root-pinned code, with writes disabled by its CLI.
    verifier_stdout = io.StringIO()
    import contextlib
    import sys
    previous_argv = sys.argv
    try:
        sys.argv = [build_path, '--verify']
        with contextlib.redirect_stdout(verifier_stdout):
            namespace['main']()
    finally:
        sys.argv = previous_argv
    assert before_files == {p.name: sha256(p.read_bytes()) for p in (REPO / FIX).iterdir() if p.is_file()}
    for path in before_files:
        assert (REPO / FIX / path).read_bytes() == blob(ROOT, FIX + path)
    blob(ROOT, 'AGENTS.md')
    changed_paths = git('diff-tree', '--no-commit-id', '--name-only', '-r', ROOT).decode().splitlines()
    assert all(p.startswith(FIX) or p in {BASE + 'journal.md', BASE + 'status.json'} for p in changed_paths)

    checks = dict(status='PASS_INDEPENDENT_BOUNDED_RECHECK', root=ROOT, original=ORIGINAL, evidence=EVIDENCE,
        original_rows=len(original['rows']), corrected_rows=len(fixed['rows']), removed_false_gaps=1,
        aliases=len(aliases), new_observations=0, source_rows_verified=len(source_checks),
        distinct_evidence_locators_before=len({source_key(r) for r in old_evidence}),
        distinct_evidence_locators_after=len({source_key(r) for r in new_evidence}),
        supporting_record_types=dict(collections.Counter(r['record_type'] for r in supporting)),
        programme_rows=len(legs), programme_source_rows_verified=len(programme_checks), original_links=len(links), actual_gaps=2,
        metric_cells=sum(x['metrics'] for x in card_checks), preserved_other_cards=9,
        all_card_non_reference_fields_unchanged=True, corrected_c33_foreign_keys=True,
        hidden_c33_false_gap=False, route_direction_year_clock_policy_unchanged=True,
        retained_original_files=len(retained), owner_source_manifest_entries=len(owner_sources),
        owner_output_manifest_entries=len(owner_outputs), owner_verify_stdout=verifier_stdout.getvalue().strip(),
        owner_verify_writes=False, original_review_status='CHANGES (user-supplied; original reviewer not contacted)',
        original_review_not_superseded=True, correction_closes_only_ROOT_DASH_01=True,
        ui_changed=False, live_or_runtime_actions=False)
    evidence = {'checks.json': checks, 'counterexamples.json': probes, 'card_invariants.json': card_checks,
        'evidence_row_checks.json': source_checks, 'numeric_alias_cells.json': numeric_cells,
        'programme_row_checks.json': programme_checks,
        'retained_original_blobs.json': retained,
        'scope_checks.json': dict(root_changed_paths=changed_paths, ui_paths_changed=[], retained_original_files=len(retained)),
        'source_manifest.json': sorted(SOURCES.values(), key=lambda r: (r['commit'], r['path']))}
    if record:
        for name, value in evidence.items():
            (HERE / name).write_bytes(encode(value))
    else:
        for name, value in evidence.items():
            assert (HERE / name).read_bytes() == encode(value), 'reviewer evidence drift: ' + name
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--record', action='store_true')
    main(parser.parse_args().record)
