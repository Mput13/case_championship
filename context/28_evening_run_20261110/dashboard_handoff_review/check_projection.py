#!/usr/bin/env python3
"""Independent exact-blob audit; writes only this review directory, no model imports."""
import collections
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SUBJECT = '5101302f93c349268f4ba0ff26832ff261e1a9e7'
SCOPE = 'context/28_evening_run_20261110/dashboard_handoff/'
CACHE = {}
TABLES = {}
CHECKS = []
EXAMPLES = []


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def blob(commit, path):
    key = (commit, path)
    if key not in CACHE:
        CACHE[key] = git('show', commit + ':' + path)
    return CACHE[key]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def git_blob(b):
    return hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()


def doc(name):
    return json.loads(blob(SUBJECT, SCOPE + name))


def rows_at(commit, path):
    key = (commit, path)
    if key not in TABLES:
        TABLES[key] = list(csv.DictReader(io.StringIO(blob(commit, path).decode('utf-8-sig'))))
    return TABLES[key]


def csv_out(name):
    return rows_at(SUBJECT, SCOPE + name)


def source_row(p):
    return rows_at(p['commit'], p['path'])[p['source_row'] - 2]


def check(name, condition, detail=None, kind='integrity'):
    CHECKS.append(dict(name=name, status='PASS' if condition else 'FAIL', kind=kind, detail=detail))


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def example(name, obj):
    EXAMPLES.append(dict(name=name, evidence=obj))


def main():
    manifest = doc('source_manifest.json')
    declared = doc('output_manifest.json')
    tracked = git('ls-tree', '-r', '--name-only', SUBJECT, SCOPE).decode().splitlines()
    inputs = []
    for path in tracked:
        b = blob(SUBJECT, path)
        inputs.append(dict(role='review_subject', commit=SUBJECT, path=path,
                           git_blob=git_blob(b), sha256=sha(b), bytes=len(b)))
    expected_files = {SCOPE + r['path'] for r in declared['outputs']} | {SCOPE + 'output_manifest.json'}
    check('exact subject tree = 70 manifest entries + manifest', set(tracked) == expected_files and len(tracked) == 71)
    for r in declared['outputs']:
        b = blob(SUBJECT, SCOPE + r['path'])
        check('output bytes ' + r['path'], len(b) == r['bytes'] and sha(b) == r['sha256'])
    check('working subject bytes unchanged', all((ROOT / p).read_bytes() == blob(SUBJECT, p) for p in tracked))
    check('129 unique exact source blobs', len(manifest['sources']) == len({(r['commit'], r['path']) for r in manifest['sources']}) == 129)
    src = {}
    for r in manifest['sources']:
        b = blob(r['commit'], r['path'])
        ok = len(b) == r['bytes'] and sha(b) == r['sha256'] and git_blob(b) == r['git_blob']
        check('upstream bytes ' + r['source_id'], ok)
        check('source identifier ' + r['source_id'], r['source_id'] == 'S' + sha((r['commit'] + ':' + r['path']).encode())[:16])
        src[r['source_id']] = r
        inputs.append(dict(role='upstream_exact_blob', **r, independently_verified=ok))
    check('source index matches manifest', len(csv_out('source_index.csv')) == 129 and all(
        all(str(v) == csv_out('source_index.csv')[i][k] for k, v in r.items())
        for i, r in enumerate(manifest['sources'])))

    pointer_count = 0
    pointer_failures = []

    def pointers(obj):
        nonlocal pointer_count
        if isinstance(obj, dict):
            if {'commit', 'path', 'source_id', 'sha256', 'git_blob'} <= obj.keys():
                pointer_count += 1
                m = src.get(obj['source_id'])
                if not m or any(obj[k] != m[k] for k in ['commit', 'path', 'sha256', 'git_blob']):
                    pointer_failures.append(obj)
                if 'source_row' in obj:
                    if not 2 <= obj['source_row'] <= len(rows_at(obj['commit'], obj['path'])) + 1:
                        pointer_failures.append(obj)
                if 'source_line' in obj:
                    if not 1 <= obj['source_line'] <= len(blob(obj['commit'], obj['path']).decode().splitlines()):
                        pointer_failures.append(obj)
                if obj.get('json_pointer'):
                    v = json.loads(blob(obj['commit'], obj['path']))
                    for k in obj['json_pointer'].split('/')[1:]:
                        k = k.replace('~1', '/').replace('~0', '~')
                        v = v[int(k)] if isinstance(v, list) else v[k]
            for v in obj.values():
                pointers(v)
        elif isinstance(obj, list):
            for v in obj:
                pointers(v)

    for path in tracked:
        if path.endswith('.json'):
            pointers(json.loads(blob(SUBJECT, path)))
    check('all JSON provenance identities and locator ranges', not pointer_failures,
          dict(pointers=pointer_count, failures=pointer_failures))

    cards = doc('cards.json')['cards']
    check('ten exact card IDs', [c['hypothesis_id'] for c in cards] == ['C01', 'C03', 'C04', 'C07', 'C10', 'C14', 'C17', 'C31', 'C33', 'C35'])
    metrics = []
    for c in cards:
        check(c['hypothesis_id'] + ' base/cautious', {'base', 'cautious'} <= {m['scenario'] for m in c['metrics']})
        check(c['hypothesis_id'] + ' no final acceptance', not c['team_accepted'] and c['market_status'] == 'NOT_ESTABLISHED' and c['full_pnl_status'] == 'UNKNOWN')
        for i, m in enumerate(c['metrics']):
            r = source_row(m['provenance'])
            ok = r[m['metric']] == m['value'] and all(r[k] == v for k, v in m['variant'].items())
            ok = ok and m['scenario'] == r.get('scenario', 'calendar_common')
            check(c['hypothesis_id'] + ':metric:' + str(i + 1) + ' exact field/variant/scenario', ok)
            check(c['hypothesis_id'] + ':metric:' + str(i + 1) + ' metadata', all(m[k] for k in ['unit', 'period', 'variant', 'accounting_boundary']))
            if m['accounting_boundary'].startswith('CASH_ONLY'):
                check(c['hypothesis_id'] + ':cash participant boundary:' + str(i + 1), all(k in m['variant'] for k in ['entity', 'kind']) and ('cash' in m['metric'] or 'funding' in m['metric']))
            metrics.append(dict(hypothesis_id=c['hypothesis_id'], **m, exact_source_field_verified=ok))
        for name, rr in c['source_tables'].items():
            check(c['hypothesis_id'] + ':source_table:' + name, all(x['values'] == source_row(x['provenance']) for x in rr))
        for scenario in ['base', 'cautious']:
            example(c['hypothesis_id'] + ':' + scenario, next(m for m in c['metrics'] if m['scenario'] == scenario))
    check('164 selected metric cells', len(metrics) == 164)
    save('metric_cells.json', metrics)

    program = doc('program_changes.json')['rows']
    context = doc('route_context.json')['rows']
    check('816 program changes', len(program) == 816)
    check('639 context rows', len(context) == 639)
    for name, rr in [('program', program), ('context', context)]:
        check(name + ' unique IDs', len(rr) == len({r['record_id'] for r in rr}))
    check('program source_fields exact', all(r['source_fields'] == source_row(r['provenance']) for r in program))
    for suffix, expected in [('/network/v2/outputs/dated_flights.csv', 146), ('/products/outputs/dated_flights.csv', 402), ('/network/v2/outputs/route_deltas.csv', 268)]:
        rr = [r for r in program if r['provenance']['path'].endswith(suffix)]
        check('all original programme source rows once: ' + suffix,
              len(rr) == expected and sorted(r['provenance']['source_row'] for r in rr) == list(range(2, expected + 2)))
    check('programme physical endpoints/date/projected scenario', all(
        r['origin'] == r['source_fields']['origin'] and r['destination'] == r['source_fields']['destination'] and
        r['route'] == '-'.join(sorted((r['origin'], r['destination']))) and
        r['date'] == r['source_fields'].get('date', r['source_fields'].get('service_date', '')) and
        r['scenario'] == r['source_fields'].get('scenario', 'calendar_common') for r in program))
    literal_context = [r for r in context if r['record_type'] != 'calculation_pair_gap']
    check('636 literal context source_fields exact', len(literal_context) == 636 and all(r['source_fields'] == source_row(r['provenance']) for r in literal_context))
    check('context complete market never inferred', all(r['complete_market'] == 'False' for r in context))
    check('context source route retained', all(r['route'] == r['source_fields'].get('route', '-'.join(sorted((r['source_fields'].get('path', '>').split('>')[0], r['source_fields'].get('path', '>').split('>')[-1])))) for r in literal_context))
    for name, rr in [('program_changes', program), ('route_context', context)]:
        cr = csv_out(name + '.csv')
        check(name + ' CSV/JSON equality', len(cr) == len(rr) and all(
            all(cr[i][k] == (json.dumps(v, ensure_ascii=False, separators=(',', ':')) if isinstance(v, (dict, list)) else str(v)) for k, v in r.items())
            for i, r in enumerate(rr)))

    dated = [r for r in program if r['record_type'] == 'dated_flight']
    deltas = [r for r in program if r['record_type'] == 'route_delta']
    check('548 flights and268 deltas remain distinct', len(dated) == 548 and len(deltas) == 268)
    check('all route deltas exact flight join', all(len(r['dated_flight_refs']) == 1 and all(
        r['source_fields'].get(k) == source_row(r['dated_flight_refs'][0]).get(k)
        for k in ['network', 'variant', 'flight_id']) for r in deltas))
    check('no alternative paths counted as flights', all(r['record_type'] not in ['alternative', 'alternative_timing'] for r in program))
    check('all card links resolve to own hypothesis', all(
        {r['record_id'] for r in program if r['hypothesis_id'] == c['hypothesis_id']} == set(c['program_change_ids']) and
        {r['record_id'] for r in context if r['hypothesis_id'] == c['hypothesis_id']} == set(c['route_context_ids']) for c in cards))
    loose = collections.defaultdict(list)
    exact = collections.defaultdict(list)
    for r in deltas:
        loose[r['flight_id']].append(r['record_id'])
        exact[(r['network'], r['variant'], r['flight_id'])].append(r['record_id'])
    example('adversarial flight_id alone collides across network/scenario', next((v for v in loose.values() if len(v) > 2), []))
    byflight = collections.defaultdict(list)
    for r in dated:
        if r['provenance']['path'].endswith('/network/v2/outputs/dated_flights.csv'):
            byflight[r['flight_id']].append(r)
    collision = next((v for v in byflight.values() if len(v) > 1), [])
    check('adversarial drop-variant join produces a real collision', len(collision) > 1 and len({r['variant'] for r in collision}) > 1)
    example('adversarial loose flight join vs exact variant', [dict(record_id=r['record_id'], flight_id=r['flight_id'], network=r['network'], variant=r['variant'], date=r['date']) for r in collision])
    c31 = [r for r in dated if r['hypothesis_id'] == 'C31' and r['network'] == 'ADD_SSJ_OMS']
    c35 = [r for r in dated if r['hypothesis_id'] == 'C35']
    check('C31 July5/8 cannot supply C35 July6/9 same-date feed', {r['date'] for r in c31} == {'2027-07-05', '2027-07-08'} and not ({r['date'] for r in c31} & {r['date'] for r in c35}))
    example('C31 vsC35 source dates', dict(C31=[r['source_fields'] for r in c31], C35_first_two=[r['source_fields'] for r in c35[:4]]))
    c35m = [m for m in metrics if m['hypothesis_id'] == 'C35']
    own = [m for m in c35m if m['metric'] == 'maximum_integration_retime_risk_K']
    ext = [m for m in c35m if m['metric'] == 'maximum_partner_price_per_reserved_seat']
    check('C35 own and external separate accounting', len(own) == 4 and len(ext) == 2 and all('OWN KEEP alternative' in m['accounting_boundary'] for m in own) and all('EXTERNAL alternative' in m['accounting_boundary'] for m in ext))
    check('C35 company growth metric not promoted', all(m['metric'] != 'incremental_rw_passenger_segments' for m in metrics))
    example('C35 distinct own/external boundaries', dict(own=own, external=ext))

    regsource = next(r for r in manifest['sources'] if r['path'].endswith('/evidence/pair_registry.csv'))
    registry = rows_at(regsource['commit'], regsource['path'])
    check('45 registry pairs and22 explicit gaps', len(registry) == 45 and sum(r['coverage_status'] == 'GAP_NOT_ABSENCE' for r in registry) == 22)
    for suffix, expected in [('/evidence/dated_service_records.csv', 359), ('/evidence/dated_service_instances.csv', 215)]:
        sr = next(r for r in manifest['sources'] if r['path'].endswith(suffix))
        check(suffix + ' count', len(rows_at(sr['commit'], sr['path'])) == expected)
    insource = next(r for r in manifest['sources'] if r['path'].endswith('/evidence/dated_service_instances.csv'))
    instances = rows_at(insource['commit'], insource['path'])
    check('12 publication conflicts retained', sum(r['clock_or_type_conflict'] == 'True' for r in instances) == 12)
    linkrows = csv_out('route_links.csv')
    check('85 immutable link rows exact', len(linkrows) == 85 and all(all(r[k] == v for k, v in source_row(json.loads(r['provenance'])).items()) for r in linkrows))
    pairs = {r['route'] for r in registry}
    gaps = [r for r in context if r['record_type'] == 'calculation_pair_gap']
    false_absence = [r for r in gaps if r['route'] in pairs]
    actual_gaps = [r for r in gaps if r['route'] not in pairs]
    check('global registry absence labels accurate', not false_absence,
          [dict(record_id=r['record_id'], route=r['route'], hypothesis_id=r['hypothesis_id']) for r in false_absence], 'semantic_finding')
    check('two other calculation legs really missing in registry', {r['route'] for r in actual_gaps} == {'TLV-ZIA', 'SVX-ZIA'})
    example('ROOT-DASH-01 independent counterexample', dict(
        registry=[dict(source_row=i + 2, values=r) for i, r in enumerate(registry) if r['route'] == 'KUF-SVX'],
        C03_context_counts=dict(collections.Counter(r['record_type'] for r in context if r['route'] == 'KUF-SVX' and r['hypothesis_id'] == 'C03')),
        C33_context=[r for r in context if r['route'] == 'KUF-SVX' and r['hypothesis_id'] == 'C33'],
        C33_affected_program_records=[r['record_id'] for r in program if r['route'] == 'KUF-SVX' and r['hypothesis_id'] == 'C33'],
        true_registry_gaps=[r['route'] for r in actual_gaps]))

    for name, expected in [('finite_options', 24), ('option_routes', 205), ('finite_option_readiness', 144), ('hypothesis_queue35', 35), ('hypothesis_decisions', 10)]:
        rr = doc('strategy/' + name + '.json')['rows']
        check(name + ' count', len(rr) == expected)
        check(name + ' exact source rows', all(all(r[k] == v for k, v in source_row(r['source_provenance']).items()) for r in rr))
        cr = csv_out('strategy/' + name + '.csv')
        check(name + ' CSV/JSON equality', len(cr) == len(rr) and all(all(
            cr[i][k] == (json.dumps(v, ensure_ascii=False, separators=(',', ':')) if isinstance(v, (dict, list)) else str(v))
            for k, v in r.items()) for i, r in enumerate(rr)))
    # All remaining strategy exports also preserve every original field.
    for path in tracked:
        if path.startswith(SCOPE + 'strategy/') and path.endswith('.json'):
            rr = json.loads(blob(SUBJECT, path))['rows']
            check(path.rsplit('/', 1)[-1] + ' all original fields', all(all(r[k] == v for k, v in source_row(r['source_provenance']).items()) for r in rr))
    options = doc('strategy/finite_options.json')['rows']
    routes = doc('strategy/option_routes.json')['rows']
    ready = doc('strategy/finite_option_readiness.json')['rows']
    optids = {r['option'] for r in options}
    check('24 unique option IDs', len(optids) == 24)
    check('205routes +144readiness foreign keys', all(r['option'] in optids for r in routes + ready))
    check('readiness unique option/branch/year', len({(r['option'], r['branch'], r['year']) for r in ready}) == 144)
    check('option route pairs agree declared count', all(
        len({tuple(sorted((r['origin'], r['destination']))) for r in routes if r['option'] == o['option']}) == int(o['model_endpoint_pairs']) for o in options))
    check('24 finite options keep author calendar', all('AUTHOR_52_48_CONCENTRATED' in r['handoff_period'] and r['source_calendar'] == 'AUTHOR_52_48_CONCENTRATED' for r in options))
    check('support shadow never awarded income', all(r['support_status'] == ('HISTORICAL_OWNER_SHADOW' if r['scenario'].endswith('_sub') else 'NONE') for r in options))
    check('MOW option status follows its actual routes', all(
        (o['physical_airports'] == 'MOW_UNRESOLVED') == any('MOW' in [r['origin'], r['destination']] for r in routes if r['option'] == o['option']) for o in options))
    annual = doc('dated_annual.json')
    check('96dated annual values exact and separate subject', len(annual['rows']) == 96 and all(r['values'] == source_row(r['provenance']) for r in annual['rows']) and annual['subject_sha'] == manifest['pins']['methods_dated'])
    queue = doc('strategy/hypothesis_queue35.json')['rows']
    check('25 reserve not economic rejection', len([r for r in queue if r['id'] not in {c['hypothesis_id'] for c in cards}]) == 25 and all(r['not_rejected_for_nonselection'] == 'True' for r in queue))
    airports = csv_out('airports.csv')
    check('MOW exists once and is unresolved', len([r for r in airports if r['code'] == 'MOW']) == 1 and all(r['latitude'] == r['longitude'] == '' and r['status'] == 'CITY_AGGREGATE_UNRESOLVED' for r in airports if r['code'] == 'MOW'))
    example('MOW projection', [r for r in airports if r['code'] == 'MOW'])

    appendix = doc('appendix_index.json')['images']
    check('14PNG exact byte identity', len(appendix) == 14 and all(
        blob(SUBJECT, SCOPE + r['local_path']) == blob(r['source_sha'], r['source_path']) and
        sha(blob(SUBJECT, SCOPE + r['local_path'])) == r['sha256'] for r in appendix))
    events = doc('acceptance_events.json')['events']
    for package in ['methods_dated', 'methods_v4']:
        ev = [e for e in events if e['subject_sha'] == manifest['pins'][package]]
        check(package + ' historical PENDING separate from exact review', len(ev) == 2 and ev[0]['historical'] and ev[0]['qualification'].startswith('PENDING') and not ev[1]['historical'] and ev[1]['qualification'] == 'APPROVE_SCOPED')
    envelope = next(e for e in events if e['subject_sha'] == manifest['pins']['methods_final'])
    check('5512 envelope packaging-only', 'PACKAGING_ONLY' in envelope['qualification'] and 'no new analytical verdict' in envelope['qualification'])
    acceptance = doc('acceptance.json')['rows']
    for package, review in [('network', 'network_review'), ('products', 'products_review'), ('evidence', 'evidence_review'), ('digital_growth', 'digital_growth_review'), ('methods_dated', 'dated_comparison_review'), ('methods_v4', 'strategy_synthesis_review')]:
        sr = next(r for r in manifest['sources'] if r['package'] == review and r['path'].endswith('/handoff.json'))
        receipt = json.loads(blob(sr['commit'], sr['path']))
        subject = next(receipt[k] for k in ['subjectSHA', 'reviewed_sha', 'subject_sha', 'subject_commit'] if k in receipt)
        check('actual exact receipt subject/verdict: ' + package,
              subject == manifest['pins'][package] and receipt['verdict'] == 'APPROVE_SCOPED' and sr['commit'] == manifest['pins'][review])
    final = csv_out('methods_final/final_acceptance.csv')
    check('eight current reviews bind exact subject/review/verdict', len(final) == 8 and all(any(
        r['subject_sha'] == f['subject_sha'] and r['review_sha'] == f['review_sha'] and r['verdict'] == f['verdict'] for r in acceptance) for f in final))
    for name in ['final_handoff.md', 'freeze.json', 'final_acceptance.csv']:
        check('5512 bytes ' + name, blob(SUBJECT, SCOPE + 'methods_final/' + name) == blob(manifest['pins']['methods_final'], 'context/28_evening_run_20261110/methods/' + name))
    check('history acceptance register retains PENDING', any('PENDING' in str(r) for r in doc('strategy/acceptance_register.json')['rows']))
    req = csv_out('requirements_coverage.csv')
    check('24 requirements with scoped qualifiers', len(req) == 24 and len({r['requirement_id'] for r in req}) == 24 and all(r['scope'] == 'This immutable data handoff, not final case acceptance' and r['exact_gap'] for r in req))
    check('roadmap explicitly not completed', next(r for r in req if r['requirement_id'] == 'R13')['status'] == 'не выполнено')

    counts = dict(subject_files=len(tracked), manifest_outputs=len(declared['outputs']), upstream_exact_blobs=len(manifest['sources']),
                  cards=len(cards), metric_cells=len(metrics), programme_rows=len(program), context_rows=len(context),
                  literal_context_rows=len(literal_context), derived_gap_rows=len(gaps), dated_flights=len(dated), route_deltas=len(deltas),
                  options=len(options), option_routes=len(routes), readiness=len(ready), annual=len(annual['rows']), png=len(appendix),
                  provenance_objects=pointer_count, checks=len(CHECKS), passed=sum(c['status'] == 'PASS' for c in CHECKS), failed=sum(c['status'] == 'FAIL' for c in CHECKS))
    save('source_manifest.json', dict(subject=SUBJECT, scope=SCOPE, policy='All bytes read via git show exactSHA:path. Review subject and upstream sources independently hashed; no moving branch reads.', inputs=inputs))
    save('checks.json', dict(subject=SUBJECT, counts=counts, checks=CHECKS, not_run=['upstream owner economic replay', 'market/fleet/award/fullPnL/cash acceptance', 'UI/browser/server/live research']))
    save('source_examples.json', dict(subject=SUBJECT, examples=EXAMPLES))
    print(json.dumps(counts, ensure_ascii=False))
    print('semantic failures:', json.dumps([c for c in CHECKS if c['status'] == 'FAIL'], ensure_ascii=False))


if __name__ == '__main__':
    main()
