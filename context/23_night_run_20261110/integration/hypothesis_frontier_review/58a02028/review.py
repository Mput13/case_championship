#!/usr/bin/env python3
"""FRONTIER_REVIEW: independent, offline oracle; all inputs via exact git show.

Does not import or execute reviewed code. Writes only beside this file.
"""
import csv
import hashlib
import io
import json
import math
import subprocess
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
PIN = '519998ed8c97ce5499f356a6d0f81558c7f6ee14'
BASE = '77343ca9dccc14d60c51d4559485646219ecd1cd'
PREFIX = 'context/23_night_run_20261110/hypothesis_frontier/'
READS, CACHE, CHECKS = {}, {}, []
ZONES = {'NJC': 'Asia/Yekaterinburg', 'UFA': 'Asia/Yekaterinburg',
         'MRV': 'Europe/Moscow', 'SVX': 'Asia/Yekaterinburg',
         'OMS': 'Asia/Omsk', 'KJA': 'Asia/Krasnoyarsk'}


def gitbytes(commit, path, grain='exact Git blob; original grain retained'):
    key = (commit, path)
    if key not in CACHE:
        blob = subprocess.check_output(['git', 'show', commit + ':' + path])
        CACHE[key] = blob
        READS[key] = dict(commit=commit, path=path, bytes=len(blob),
                          git_blob=subprocess.check_output(
                              ['git', 'rev-parse', commit + ':' + path], text=True).strip(),
                          sha256=hashlib.sha256(blob).hexdigest(), grain=grain,
                          acquisition='git show exactSHA:path; no working-tree input')
    elif grain != 'exact Git blob; original grain retained':
        READS[key]['grain'] = grain
    return CACHE[key]


def text(path):
    return gitbytes(PIN, PREFIX + path).decode()


def rows(path):
    return list(csv.DictReader(io.StringIO(text(path))))


def obj(path):
    return json.loads(text(path))


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def table(name, data):
    assert data, name
    with (ROOT / name).open('w', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def check(ident, ok, detail):
    CHECKS.append(dict(check_id=ident, status='PASS' if ok else 'FAIL',
                       personally_executed=True, detail=detail))


def eq(ident, actual, expected):
    check(ident, actual == expected, dict(actual=actual, expected=expected))


def dt(s):
    return datetime.fromisoformat(s)


def mins(later, earlier):
    return (later - earlier).total_seconds() / 60


def main():
    for f in ['contract.md', 'briefs/hypothesis_frontier_review.md']:
        gitbytes(BASE, 'context/23_night_run_20261110/' + f, 'review contract')
    # Read and fingerprint every reviewed blob without copying source/raw inputs.
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', PIN,
                                     '--', PREFIX], text=True).splitlines()
    for p in paths:
        gitbytes(PIN, p)
    manifest = obj('source_manifest.json')
    verifications = []
    for entry in manifest['inputs']:
        stored = gitbytes(PIN, PREFIX + entry['stored_path'], entry['grain'])
        upstream = gitbytes(entry['source_commit'], entry['source_path'], entry['grain'])
        good = (stored == upstream and len(stored) == entry['bytes'] and
                hashlib.sha256(stored).hexdigest() == entry['sha256'] and
                READS[entry['source_commit'], entry['source_path']]['git_blob'] == entry['git_blob'])
        verifications.append(dict(input_id=entry['input_id'], exact_upstream_equal=good,
                                  source_commit=entry['source_commit'],
                                  source_path=entry['source_path'], grain=entry['grain']))
    check('PINNED_56_UPSTREAM_BLOBS', all(r['exact_upstream_equal'] for r in verifications),
          dict(count=len(verifications), bytes=sum(e['bytes'] for e in manifest['inputs'])))
    output_manifest = obj('output_manifest.json')
    bad_outputs = [e['path'] for e in output_manifest['files']
                   if len(gitbytes(PIN, PREFIX + e['path'])) != e['bytes'] or
                   hashlib.sha256(gitbytes(PIN, PREFIX + e['path'])).hexdigest() != e['sha256']]
    check('AUTHOR_OUTPUT_MANIFEST', not bad_outputs,
          dict(files=len(output_manifest['files']), mismatches=bad_outputs))
    save('input_verification.json', verifications)

    # Compare complete specifications, including author, ancestors and original status.
    specs = rows('inputs/hypotheses/candidates.csv')
    catalog = obj('inputs/hypotheses/inputs/candidate_catalog.json')['candidates']
    inv = rows('inventory35.csv')
    ancestors = {r['id']: r for r in rows('inputs/hypotheses/existing_hypotheses.csv')}
    queue = rows('experiment_queue.csv')
    selected = {t['candidate_id'] for t in obj('test_contract.json')['tests']}
    mapping = {'title': 'title', 'author_ref': 'author', 'ancestor_ids': 'ancestor_ids',
               'family_provenance': 'family_provenance', 'author_network_form': 'network_form',
               'author_operating_base': 'operating_base', 'author_paths': 'proposed_paths',
               'author_passenger_purpose': 'passenger_and_purpose', 'author_season_stay': 'season_and_stay',
               'author_current_alternative': 'current_alternative', 'author_product': 'rw_product',
               'author_competitor_response': 'competitor_and_response', 'author_frequency': 'frequency_proposal',
               'author_resource_requirement': 'resource_requirement', 'author_stop_rule': 'stop_rule',
               'author_specific_test': 'specific_test', 'author_data_request_ids': 'data_request_ids',
               'author_demand_status': 'demand_status', 'author_net_fare_status': 'net_fare_status',
               'author_resource_status': 'resource_status', 'author_evaluation_status': 'evaluation_status'}
    eq('ALL35_EXACT_ORDER', [r['candidate_id'] for r in inv], [f'C{i:02}' for i in range(1, 36)])
    catalog_by = {r['candidate_id']: r for r in catalog}
    inventory_by = {r['candidate_id']: r for r in inv}
    classified = []
    for r in specs:
        i = inventory_by[r['candidate_id']]
        c = catalog_by[r['candidate_id']]
        # CSV exports JSON null as an empty field. Preserve this representation
        # boundary instead of treating null/empty serialization as changed data.
        cat_mismatches = [k for k, v in r.items() if ('' if c[k] is None else str(c[k])) != v]
        mismatches = [k for k, v in mapping.items() if i[k] != r[v]]
        missing_ancestors = [a for a in r['ancestor_ids'].split(';') if a not in ancestors]
        classified.append(dict(candidate_id=r['candidate_id'], title=r['title'],
                               author_ref=r['author'], ancestor_ids=r['ancestor_ids'],
                               ancestor_original_authors='; '.join(ancestors[a]['original_author']
                                   for a in r['ancestor_ids'].split(';') if a in ancestors),
                               inventory_fields_equal=not mismatches,
                               catalog_fields_equal=not cat_mismatches,
                               all_ancestors_resolve=not missing_ancestors,
                               author_evaluation_status=r['evaluation_status'],
                               current_test='SELECTED_BOUNDED_TEST' if r['candidate_id'] in selected else 'NOT_TESTED_HERE_NO_NEGATIVE_INFERENCE',
                               main_unknown=i['main_unresolved_parameter'],
                               next_test=i['source_or_experiment_that_can_change_conclusion']))
    check('ALL35_AUTHOR_ANCESTOR_FIELDS', all(r['inventory_fields_equal'] and r['catalog_fields_equal']
          and r['all_ancestors_resolve'] for r in classified), dict(rows=35, mapped_fields=len(mapping)))
    check('ALL35_ORIGINAL_UNKNOWN', all(r['evaluation_status'] == 'NOT_EVALUATED' and
          r['demand_status'] == r['net_fare_status'] == r['resource_status'] == 'UNKNOWN' and
          not r['demand_value'] and not r['net_fare_rub'] and not r['available_aircraft'] for r in specs), 35)
    eq('THREE_CURRENT_TESTS', sorted(selected), ['C01', 'C07', 'C14'])
    check('INVENTORY_PIN_AND_PROPOSAL_SCOPE', all(r['source_commit'] == '6ed8788882e7b4d07044b4f6e686ff71eadd8ac5'
          and r['input_set_id'] == 'frontier-frozen-001' and r['classification'] == 'AGENT_PROPOSAL' for r in inv), 35)
    eq('32_UNTESTED_RETAINED', sum(r['candidate_id'] not in selected for r in specs), 32)
    queued = {c for r in queue for c in r['candidate_ids'].split(';')}
    eq('QUEUE_PRESERVES_ALL35', sorted(queued), sorted(r['candidate_id'] for r in specs))
    features = rows('feature_admission.csv')
    statuses = {r['feature_id']: r['status'] for r in features}
    eq('WEATHER_NOT_PREDICTIVE', statuses['WEATHER'], 'NOT_RUN_NO_OPERATIONAL_LABELS')
    eq('TOURISM_NOT_OD', statuses['TOURISM'], 'NOT_RUN_NO_ENDPOINT_OD')
    check('GEOMETRY_NOT_DISPATCH', all(r['geometry_acceptance'] == 'SCENARIO_SCREEN_ONLY_NOT_DISPATCH' for r in inv), 35)
    table('independent_inventory35.csv', classified)
    table('feature_scope_review.csv', [dict(feature_id=r['feature_id'], status=r['status'],
          mechanism=r['decision_mechanism'], admission_condition=r['admission_condition'],
          personal_scope='Classification checked; no outcome/holdout/ablation executed') for r in features])

    frozen = rows('inputs/experiment/runs/c26661067277af20/physical_legs.csv')
    program = obj('inputs/experiment/scenario_programs.json')
    dates = program['operating_dates']
    base = {(r['origin'], r['destination']): r for r in frozen
            if r['variant'] == 'C01_unsync' and r['departure_utc'].startswith(dates[0])}
    n_arr, n_dep = dt(base['NJC', 'UFA']['arrival_utc']), dt(base['UFA', 'NJC']['departure_utc'])
    s_dep, s_arr = dt(base['UFA', 'MRV']['departure_utc']), dt(base['UFA', 'MRV']['arrival_utc'])
    r_dep, r_arr = dt(base['MRV', 'UFA']['departure_utc']), dt(base['MRV', 'UFA']['arrival_utc'])
    eq('C01_BASELINE_WAITS_TURN', [mins(s_dep, n_arr), mins(n_dep, r_arr), mins(r_dep, s_arr)], [-60, 195, 45])
    # Exhaustive oracle uses clock inequalities, not the author's bound function.
    bounds, slices, vertices, c01_cases, leg_checks = [], [], [], [], []
    author_bounds = {r['scenario_id']: r for r in rows('runs/hf01/retiming_boundaries.csv')}
    author_legs = {(r['scenario_id'], r['source_leg_id']): r for r in rows('runs/hf01/physical_legs.csv')}
    generated = {}
    for m in [45, 60, 90]:
        for turn in [30, 45, 60]:
            ident = f'HF01_M{m}_T{turn}'
            solutions = []
            for x in range(241):
                for y in range(196):
                    ow = mins(s_dep + timedelta(minutes=x), n_arr)
                    iw = mins(n_dep, r_arr + timedelta(minutes=y))
                    ground = mins(r_dep + timedelta(minutes=y), s_arr + timedelta(minutes=x))
                    if m <= ow <= 180 and m <= iw <= 180 and ground >= turn:
                        solutions.append((x, y))
            xmin, xmax, ymin, ymax = m + 60, min(240, 240 - m - turn), m + turn + 15, 195 - m
            feasible = 2 * m + turn <= 180
            formula = {(x, y) for x in range(241) for y in range(196)
                       if xmin <= x <= xmax and max(15, x + turn - 45) <= y <= ymax}
            eq('C01_POLYGON_' + ident, sorted(formula), sorted(solutions))
            # Large point sets are not duplicated in check detail; save slices instead.
            CHECKS[-1]['detail'] = dict(grid_pairs=241 * 196, feasible_pairs=len(solutions),
                                        mask_mismatches=len(formula.symmetric_difference(solutions)))
            b = author_bounds[ident]
            expected = {'south_departure_shift_min_minutes': xmin, 'south_departure_shift_max_minutes': xmax,
                        'south_return_shift_min_minutes': ymin if feasible else None,
                        'south_return_shift_max_minutes': ymax,
                        'max_connection_minimum_given_turn_minutes': (180 - turn) / 2}
            mismatches = [k for k, v in expected.items() if (float(b[k]) if b[k] else None) != v]
            check('C01_BOUND_COLUMNS_' + ident, not mismatches and (b['feasible'] == 'True') == feasible,
                  dict(expected=expected, mismatched_fields=mismatches))
            bounds.append(dict(scenario_id=ident, M=m, T=turn, joint_feasible=feasible,
                               x_min=xmin, x_max=xmax, y_min_global=ymin if feasible else None,
                               y_max=ymax, y_min_conditional='max(15,x+T-45)', feasible_integer_pairs=len(solutions),
                               earliest_south_elapsed=300 + turn if feasible else None,
                               return_earlier_than_sync=135 - ymin if feasible else None))
            grouped = defaultdict(list)
            for x, y in solutions:
                grouped[x].append(y)
            for x, ys in grouped.items():
                slices.append(dict(scenario_id=ident, x=x, minimum_y=min(ys), maximum_y=max(ys), integer_pairs=len(ys)))
            if feasible:
                for x, y in sorted({(xmin, ymin), (xmin, ymax), (xmax, ymax)}):
                    vertices.append(dict(scenario_id=ident, x=x, y=y))
                for source in [r for r in frozen if r['variant'] == 'C01_unsync']:
                    shift = xmin if (source['origin'], source['destination']) == ('UFA', 'MRV') else ymin if (source['origin'], source['destination']) == ('MRV', 'UFA') else 0
                    start, finish = dt(source['departure_utc']) + timedelta(minutes=shift), dt(source['arrival_utc']) + timedelta(minutes=shift)
                    generated[ident, source['departure_utc'][:10], source['origin'], source['destination']] = (start, finish)
                    target = author_legs[ident, source['leg_id']]
                    local_start, local_finish = start.astimezone(ZoneInfo(ZONES[source['origin']])), finish.astimezone(ZoneInfo(ZONES[source['destination']]))
                    good = all(dt(target[k]) == v and target[k] == v.isoformat() for k, v in
                               [('departure_utc', start), ('arrival_utc', finish), ('departure_local', local_start), ('arrival_local', local_finish)])
                    good = good and float(target['block_minutes']) == mins(finish, start) == float(source['block_minutes']) and target['tail'] == source['tail'] and target['nominal_seats'] == source['nominal_seats']
                    leg_checks.append(dict(test='HF01', scenario_id=ident, source_leg_id=source['leg_id'],
                                            origin=source['origin'], destination=source['destination'],
                                            departure_utc=start.isoformat(), arrival_utc=finish.isoformat(),
                                            departure_local=local_start.isoformat(), arrival_local=local_finish.isoformat(), exact_author_equal=good))
            for initial in [dates[0], dates[1]]:
                for nights in [7, 10, 14]:
                    checkout = date.fromisoformat(initial) + timedelta(days=nights)
                    matched = feasible and checkout.isoformat() in dates
                    home = generated[ident, checkout.isoformat(), 'UFA', 'NJC'][1].astimezone(ZoneInfo(ZONES['NJC'])).date().isoformat() if matched else None
                    c01_cases.append(dict(scenario_id=ident, departure_date=initial, hotel_nights=nights,
                                           booked_checkout_date=checkout.isoformat(), return_home_date=home,
                                           gate='DATE_AND_CLOCK_SCENARIO_PASS' if matched else 'NO_RETURN_DATE_IN_SCENARIO' if feasible else 'CONNECTION_TURN_INFEASIBLE'))
    a_cases = {(r['scenario_id'], r['departure_date'], int(r['hotel_nights'])): r for r in rows('runs/hf01/dated_products.csv')}
    check('C01_ALL54_DATED_PRODUCTS', len(a_cases) == len(c01_cases) == 54 and all(
          all((a_cases[r['scenario_id'], r['departure_date'], r['hotel_nights']][k] or None) == r[k]
              for k in ['booked_checkout_date', 'return_home_date', 'gate']) for r in c01_cases), dict(rows=len(c01_cases)))
    check('C01_MON_FRI_NEXT_CIVIL_DAY', all(date.fromisoformat(d).weekday() in [0, 4] for d in dates) and
          all(date.fromisoformat(r['return_home_date']) == date.fromisoformat(r['booked_checkout_date']) + timedelta(days=1)
              for r in c01_cases if r['return_home_date']), 'Six operating dates; every matched return home at next-day00:00+05')
    eq('C01_5_OF_6', Counter(r['scenario_id'] for r in c01_cases if r['gate'] == 'DATE_AND_CLOCK_SCENARIO_PASS'),
       Counter({r['scenario_id']: 5 for r in bounds if r['joint_feasible']}))
    c01_deadlines = []
    for r in rows('runs/hf01/return_deadlines.csv'):
        b = next(b for b in bounds if b['scenario_id'] == r['scenario_id'])
        expected = b['joint_feasible'] and b['y_min_global'] <= int(r['allowed_return_slip_minutes'])
        c01_deadlines.append(dict(scenario_id=r['scenario_id'], limit=int(r['allowed_return_slip_minutes']), pass_oracle=expected,
                                   author_equal=(r['gate'] == 'FEASIBLE_SCENARIO_TIMES') == expected))
    check('C01_ALL54_RETURN_LIMITS', len(c01_deadlines) == 54 and all(r['author_equal'] for r in c01_deadlines), 54)
    special = next(r for r in bounds if r['scenario_id'] == 'HF01_M60_T45')
    eq('C01_M60_T45_EARLIEST', [special['x_min'], special['y_min_global'],
       -60+special['x_min'], 195-special['y_min_global'], special['earliest_south_elapsed'],
       special['return_earlier_than_sync']], [120, 120, 60, 75, 345, 15])
    frozen_calendar = []
    for r in rows('inputs/experiment/runs/c26661067277af20/c01_dated_cohorts.csv'):
        initial = r['outbound_origin_date']
        checkout = date.fromisoformat(initial) + timedelta(days=int(r['hotel_nights']))
        initial_legs = {(a['origin'], a['destination']): a for a in frozen
                        if a['variant'] == r['variant'] and a['departure_utc'].startswith(initial)}
        outbound_wait = mins(dt(initial_legs['UFA', 'MRV']['departure_utc']), dt(initial_legs['NJC', 'UFA']['arrival_utc']))
        inward_wait = mins(dt(initial_legs['UFA', 'NJC']['departure_utc']), dt(initial_legs['MRV', 'UFA']['arrival_utc']))
        M = int(r['min_connection_minutes'])
        passed = checkout.isoformat() in dates and M <= outbound_wait <= 180 and M <= inward_wait <= 180
        # A known return-flight date remains known when a connection fails.
        home = (checkout + timedelta(days=1)).isoformat() if checkout.isoformat() in dates else ''
        frozen_calendar.append(dict(variant=r['variant'], initial_date=initial, nights=int(r['hotel_nights']), M=M,
                                    checkout=checkout.isoformat(), date_present=checkout.isoformat() in dates, date_clock_match=passed,
                                    home_date=home, author_equal=(r['calendar_gate'] == 'PASS_SCENARIO_CALENDAR') == passed
                                    and r['return_home_arrival_date'] == home and r['checkout_local'] == checkout.isoformat()))
    check('FROZEN_C01_ALL36_CALENDAR_ROWS', len(frozen_calendar) == 36 and all(r['author_equal'] for r in frozen_calendar),
          dict(rows=36, matched=sum(r['date_clock_match'] for r in frozen_calendar)))
    table('independent_frozen_c01_calendar.csv', frozen_calendar)
    continuity = []
    for ident in {r['scenario_id'] for r in bounds if r['joint_feasible']}:
        for day in dates:
            for tail, pairs in [('NORTH', [('NJC','UFA'), ('UFA','NJC')]), ('SOUTH', [('UFA','MRV'), ('MRV','UFA')])]:
                first = generated[ident, day, *pairs[0]]
                last = generated[ident, day, *pairs[1]]
                ground = mins(last[0], first[1])
                T = int(ident.split('_T')[-1])
                continuity.append(dict(scenario_id=ident, date=day, tail=tail,
                                       start_position=pairs[0][0], end_position=pairs[1][1],
                                       occupied_minutes=mins(last[1], first[0]), ground_minutes=ground,
                                       continuity_pass=pairs[0][1] == pairs[1][0] and first[0] < first[1] <= last[0] < last[1]
                                       and ground >= T and pairs[0][0] == pairs[1][1]))
    check('C01_72_TAIL_DATE_CONTINUITY', len(continuity) == 72 and all(r['continuity_pass'] for r in continuity),
          'Hypothetical tail starts/ends and turn; no actual resource admission')
    table('independent_c01_resource.csv', sorted(continuity, key=lambda r:(r['scenario_id'],r['date'],r['tail'])))
    table('independent_c01_boundaries.csv', bounds)
    table('independent_c01_joint_slices.csv', slices)
    table('independent_c01_vertices.csv', vertices)
    table('independent_c01_calendar.csv', c01_cases)
    table('independent_c01_return_limits.csv', c01_deadlines)

    # C07 reconstructed from source timetable clocks + four durations, independent of chain outputs.
    source_timetable = rows('inputs/experiment/inputs/core/omsk_domestic_timetable_rows.csv')
    timetable = {r['source_text_line']: r for r in source_timetable}
    eq('C07_SOURCE_CLOCKS_68', [timetable['68'][k] for k in ['preceding_origin_departure_local_raw', 'omsk_arrival_local_raw', 'omsk_departure_local_raw', 'onward_arrival_local_raw']], ['21.20', '00.00', '00.50', '01.35'])
    reference = sorted([r for r in frozen if r['variant'] == 'C07_reference'], key=lambda r: r['departure_utc'])
    start, end = dt(reference[0]['departure_utc']), dt(reference[-1]['arrival_utc'])
    eq('C07_REFERENCE_TIME_BLOCK', [mins(end, start), sum(mins(dt(r['arrival_utc']), dt(r['departure_utc'])) for r in reference)], [255, 205])
    # Derive the directional clock proxies in their respective local zones.
    # OMS00:30 and SVX/OMS00:00 anchor their remote preceding date conditionally.
    def clock(day, value, airport):
        return datetime.fromisoformat(day+'T'+value.replace('.', ':')).replace(tzinfo=ZoneInfo(ZONES[airport]))
    derived_reference_start = clock('2026-12-08', timetable['68']['preceding_origin_departure_local_raw'], 'SVX').astimezone(timezone.utc)
    derived_reference_end = clock('2026-12-09', timetable['68']['onward_arrival_local_raw'], 'SVX').astimezone(timezone.utc)
    eq('C07_REFERENCE_DATES_FROM_LOCAL_CLOCKS', [start.isoformat(), end.isoformat()],
       [derived_reference_start.isoformat(), derived_reference_end.isoformat()])
    chain_durations = [
        mins(clock('2026-12-09', timetable['68']['omsk_arrival_local_raw'], 'OMS'), derived_reference_start),
        mins(clock('2026-12-12', timetable['79']['onward_arrival_local_raw'], 'KJA'),
             clock('2026-12-12', timetable['79']['omsk_departure_local_raw'], 'OMS')),
        mins(clock('2026-12-12', timetable['79']['omsk_arrival_local_raw'], 'OMS'),
             clock('2026-12-11', timetable['79']['preceding_origin_departure_local_raw'], 'KJA')),
        mins(derived_reference_end, clock('2026-12-09', timetable['68']['omsk_departure_local_raw'], 'OMS'))]
    eq('C07_FOUR_BLOCK_PROXIES_FROM_LOCAL_CLOCKS', chain_durations, [100,125,145,105])
    routes = [('SVX', 'OMS'), ('OMS', 'KJA'), ('KJA', 'OMS'), ('OMS', 'SVX')]
    c07_cases, c07_limits, c07_sides = [], [], []
    a07 = {r['scenario_id']: r for r in rows('runs/hf07/return_advance_boundaries.csv')}
    a07legs = {(r['scenario_id'], r['origin'], r['destination']): r for r in rows('runs/hf07/physical_legs.csv')}
    for turn in [30, 45, 60]:
        source_chain = sorted([r for r in frozen if r['variant'] == f'C07_chain_turn{turn}'], key=lambda r: r['departure_utc'])
        eq(f'C07_PROXY_BLOCKS_T{turn}', [mins(dt(r['arrival_utc']), dt(r['departure_utc'])) for r in source_chain], chain_durations)
        for slack in [0, 180, 310, 355, 400, 600]:
            ident = f'HF07_T{turn}_L{slack}'
            elapsed = sum(chain_durations) + 3 * turn
            delta = elapsed - mins(end, start)
            advance = max(0, delta - slack)
            shifted_start = start - timedelta(minutes=advance)
            finish = shifted_start + timedelta(minutes=elapsed)
            target = a07[ident]
            fields = {'chain_elapsed_minutes': elapsed, 'delta_elapsed_minutes': delta,
                      'chain_block_minutes': sum(chain_durations), 'delta_block_minutes': 270,
                      'required_departure_advance_minutes': advance}
            exact = all(float(target[k]) == v for k, v in fields.items()) and dt(target['deadline_utc']) == end + timedelta(minutes=slack)
            exact = exact and target['departure_svx_local_at_minimum_advance'] == shifted_start.astimezone(ZoneInfo(ZONES['SVX'])).isoformat() and target['candidate_return_svx_local'] == finish.astimezone(ZoneInfo(ZONES['SVX'])).isoformat()
            c07_cases.append(dict(scenario_id=ident, T=turn, L=slack, block_minutes=sum(chain_durations), elapsed_minutes=elapsed,
                                   delta_elapsed_minutes=delta, required_advance=advance,
                                   departure_svx_local=shifted_start.astimezone(ZoneInfo(ZONES['SVX'])).isoformat(),
                                   return_svx_local=finish.astimezone(ZoneInfo(ZONES['SVX'])).isoformat(),
                                   return_base_leg_shift_minutes=delta-advance, outbound_base_leg_shift_minutes=-advance,
                                   exact_author_equal=exact))
            for try_advance in sorted({max(0, advance - 1), advance, advance + 1}):
                candidate_finish = start - timedelta(minutes=try_advance) + timedelta(minutes=elapsed)
                c07_sides.append(dict(scenario_id=ident, advance_tested=try_advance, required_advance=advance,
                                       delta_from_deadline_minutes=mins(candidate_finish, end + timedelta(minutes=slack)),
                                       deadline_pass=candidate_finish <= end + timedelta(minutes=slack)))
            cursor = shifted_start
            for idx, ((origin, destination), duration) in enumerate(zip(routes, chain_durations)):
                arrival = cursor + timedelta(minutes=duration)
                target_leg = a07legs[ident, origin, destination]
                local_start, local_end = cursor.astimezone(ZoneInfo(ZONES[origin])), arrival.astimezone(ZoneInfo(ZONES[destination]))
                exact_leg = all(target_leg[k] == v.isoformat() for k, v in [('departure_utc', cursor), ('arrival_utc', arrival), ('departure_local', local_start), ('arrival_local', local_end)])
                leg_checks.append(dict(test='HF07', scenario_id=ident, source_leg_id=target_leg['source_leg_id'], origin=origin, destination=destination,
                                        departure_utc=cursor.isoformat(), arrival_utc=arrival.isoformat(), departure_local=local_start.isoformat(),
                                        arrival_local=local_end.isoformat(), exact_author_equal=exact_leg))
                cursor = arrival + timedelta(minutes=turn)
            for allowance in [0, 180, 355]:
                c07_limits.append(dict(scenario_id=ident, allowance=allowance, required_advance=advance,
                                        gate='PASS_SCENARIO_RETURN_LIMIT' if allowance >= advance else 'FAIL_SCENARIO_RETURN_LIMIT'))
    eq('C07_18_CASES', len(c07_cases), 18)
    check('C07_18_TIMES_AND_DATES', all(r['exact_author_equal'] for r in c07_cases), 18)
    a_limits = {(r['scenario_id'], int(r['advance_allowance_minutes'])): r['gate'] for r in rows('runs/hf07/advance_limits.csv')}
    check('C07_54_ADVANCE_ALLOWANCES', len(a_limits) == 54 and all(a_limits[r['scenario_id'], r['allowance']] == r['gate'] for r in c07_limits), 54)
    eq('C07_NEGATIVE_LIMIT_ROWS_RETAINED', sum(r['gate'].startswith('FAIL') for r in c07_limits), 14)
    check('C07_ONE_MINUTE_BELOW_FAILS', all(not r['deadline_pass'] for r in c07_sides if r['advance_tested'] < r['required_advance']),
          dict(active_deadlines=sum(r['required_advance'] > 0 for r in c07_cases), inactive_minimum_zero=sum(r['required_advance'] == 0 for r in c07_cases)))
    check('ALL216_LEG_TIMESTAMPS', len(leg_checks) == 216 and all(r['exact_author_equal'] for r in leg_checks), dict(HF01=144, HF07=72))
    table('independent_leg_times.csv', leg_checks)
    table('independent_c07_boundaries.csv', c07_cases)
    table('independent_c07_limit_cases.csv', c07_limits)
    table('independent_c07_boundary_sides.csv', c07_sides)

    # C14 oracle builds the 24 requests afresh from dated flights x properties x basis x nights.
    flights = rows('inputs/experiment/inputs/alternative_fa39de4/normalized/dated_flights.csv')
    properties = rows('inputs/experiment/inputs/alternative_fa39de4/stay_offer/stay_rules.csv')
    offers = rows('inputs/experiment/inputs/alternative_fa39de4/stay_offer/public_offers.csv')
    original_products = rows('inputs/experiment/c14_products/3906edd033f75bc6/flight_hotel_calendar.csv')
    original_by = {(r['outbound_instance_id'], r['property_id'], r['stay_basis'], int(r['hotel_nights'])): r for r in original_products}
    outbounds = [r for r in flights if r['origin_iata'] == 'KVX' and r['departure_local_date'] in ['2026-12-07', '2026-12-10']]
    returns = sorted([r for r in flights if r['origin_iata'] == 'MRV' and r['destination_iata'] == 'KVX'], key=lambda r: dt(r['departure_utc']))
    requests, policies = [], []
    a14 = {(r['product_request_id'], int(r['max_additional_booked_nights'])): r for r in rows('runs/hf14/bookability_tolerance.csv')}
    for f in outbounds:
        for prop in properties:
            for basis, startkey in [('BOOK_DEPARTURE_DATE_REQUIRES_LATE_ADMISSION', 'departure_local_date'), ('BOOK_AIRPORT_ARRIVAL_DATE_REGULAR_CHECKIN', 'arrival_local_date')]:
                for nights in [7, 10, 14]:
                    booked_start = date.fromisoformat(f[startkey])
                    checkout = booked_start + timedelta(days=nights)
                    p = original_by[f['instance_id'], prop['property_id'], basis, nights]
                    exact_return = next((r for r in returns if r['departure_local_date'] == checkout.isoformat()), None)
                    next_return = next((r for r in returns if date.fromisoformat(r['departure_local_date']) >= checkout), None)
                    extra = (date.fromisoformat(next_return['departure_local_date']) - checkout).days if next_return else None
                    request_good = p['booked_checkin_local_date'] == booked_start.isoformat() and p['booked_checkout_local_date'] == checkout.isoformat() and p['return_instance_id'] == (exact_return['instance_id'] if exact_return else '')
                    combination = '|'.join([f['instance_id'], basis, str(nights)])
                    requests.append(dict(outbound_id=f['instance_id'], property_id=prop['property_id'], stay_basis=basis,
                                          original_nights=nights, booked_start=booked_start.isoformat(), checkout=checkout.isoformat(),
                                          earliest_return=next_return['departure_local_date'] if next_return else None,
                                          minimum_extra_nights=extra, distinct_date_stay_id=combination, exact_frozen_request_equal=request_good))
                    for limit in [0, 1, 2, 3]:
                        gate = 'UNKNOWN_AFTER_CAPTURE' if next_return is None else 'DATE_MATCH_ONLY' if extra <= limit else 'NEEDS_MORE_BOOKED_NIGHTS_THAN_ALLOWED'
                        a = a14[p['product_request_id'], limit]
                        good = (a['date_gate'] == gate and (int(a['minimum_additional_booked_nights']) if a['minimum_additional_booked_nights'] else None) == extra
                                and (a['next_captured_return_id'] or None) == (next_return['instance_id'] if next_return else None))
                        policies.append(dict(distinct_date_stay_id=combination, property_id=prop['property_id'], limit=limit,
                                               checkout=checkout.isoformat(), extra_nights=extra, gate=gate, exact_author_equal=good))
    check('C14_24_REQUESTS_FROM_FLIGHTS', len(requests) == len(original_by) == 24 and all(r['exact_frozen_request_equal'] for r in requests), 24)
    check('C14_ALL96_POLICIES', len(policies) == len(a14) == 96 and all(r['exact_author_equal'] for r in policies), 96)
    summaries = []
    for limit in [0, 1, 2, 3]:
        matching = [r for r in policies if r['limit'] == limit and r['gate'] == 'DATE_MATCH_ONLY']
        unknown = [r for r in policies if r['limit'] == limit and r['gate'] == 'UNKNOWN_AFTER_CAPTURE']
        summaries.append(dict(limit=limit, date_matched_distinct=len({r['distinct_date_stay_id'] for r in matching}),
                               date_matched_property_rows=len(matching), unknown_property_rows=len(unknown),
                               total_distinct=12, total_properties=24, full_product_acceptance=None))
    eq('C14_DISTINCT_6_7_9_11', [r['date_matched_distinct'] for r in summaries], [6, 7, 9, 11])
    check('C14_25DEC_UNKNOWN_RETAINED', all(r['unknown_property_rows'] == 2 for r in summaries) and
          {r['checkout'] for r in requests if r['earliest_return'] is None} == {'2026-12-25'},
          'One distinct request/two properties; latest captured return24Dec; no inference of no service')
    null_fields = ['additional_stay_price_rub', 'rw_airline_revenue_rub', 'physical_seat_segments_per_oneway_product', 'rw_operating_flight_delta']
    check('C14_NULL_MONEY_LEGS_AND_BOOKING', all(not r[k] for r in a14.values() for k in null_fields) and
          all(r['current_full_product_gate'] == 'UNKNOWN_NOT_ESTABLISHED' and r['ground_transfer'] == 'UNKNOWN' and r['hotel_admission'] == 'UNKNOWN' for r in a14.values()),
          dict(rows=96, null_fields=null_fields))
    check('C14_DAY_TARIFF_NOT_NIGHT_PRICE', all(r['price_unit'] in ['PERSON_BED_DAY', 'PERSON_DAY'] and r['billing_days_for_requested_nights'] == 'UNKNOWN' for r in offers),
          dict(tariff_units=[r['price_unit'] for r in offers], multiplication_performed=False))
    table('independent_c14_requests.csv', requests)
    table('independent_c14_policy_rows.csv', policies)
    table('independent_c14_distinct_summary.csv', summaries)

    # Four mechanical capacity fixtures; derive the integer threshold by feasible quantity search.
    a_fixtures = rows('runs/economics/capacity_conditioned_thresholds.csv')
    allocations = rows('runs/economics/fixture_capacity_allocation.csv')
    itineraries = rows('runs/economics/fixture_itinerary.csv')
    econ = []
    for c, used_legs in [('C01', 2), ('C07', 1)]:
        for K in [300000, 500000]:
            ident = f'{c}_G{K}'
            margin, residual = 8000 - 500, 100 - 80
            q = next(n for n in range(101) if 2 * n * margin >= K)
            author = next(r for r in a_fixtures if r['fixture_id'] == ident)
            expected = {'required_q_each_direction': q, 'residual_each_leg': residual,
                        'endpoint_journeys': 2*q, 'physical_boardings': 2*q*used_legs,
                        'through_fare_applications': 2*q, 'ticket_revenue_once_rub': 2*q*8000,
                        'threshold_contribution_rub': 2*q*margin-K,
                        'contribution_one_journey_each_direction_below_rub': 2*(q-1)*margin-K,
                        'maximum_new_contribution_with_locals_preserved_rub': 2*residual*margin}
            good = all(int(author[k]) == v for k, v in expected.items()) and (author['capacity_gate'] == 'PASS_FIXTURE_ONLY') == (q <= residual)
            al = [r for r in allocations if r['fixture_id'] == ident]
            journeys = [r for r in itineraries if r['fixture_id'] == ident]
            loads_good = len(al) == 2*used_legs and len(journeys) == 2 and all(int(r['total_load']) == 80+q and (r['gate'] == 'PASS') == (80+q <= 100) for r in al)
            for trip in journeys:
                trip_legs = trip['leg_ids'].split(';')
                loads_good = loads_good and len(trip_legs) == len(set(trip_legs)) == used_legs and int(trip['ticket_revenue']) == q*8000 and int(trip['physical_boardings']) == q*used_legs
                loads_good = loads_good and all(sum(int(r['new_journeys']) for r in al if r['leg_id'] == leg) == q for leg in trip_legs)
            econ.append(dict(fixture_id=ident, candidate_id=c, K_fixed=K, margin=margin, residual_each_leg=residual,
                             required_q_each_direction=q, maximum_contribution=2*residual*margin,
                             total_load_per_leg=80+q, capacity_gate='PASS_FIXTURE_ONLY' if q <= residual else 'FAIL_PRESERVING_LOCALS',
                             endpoint_journeys=2*q, seat_segments=2*q*used_legs, fare_applications=2*q,
                             exact_author_equal=good and loads_good, actual_sales=None, actual_margin=None, actual_K_q=None, actual_full_budget=None))
    check('FOUR_CAPACITY_FIXTURES', len(econ) == 4 and all(r['exact_author_equal'] for r in econ), econ)
    terms = rows('runs/economics/monetary_difference_terms.csv')
    check('ALL18_MONEY_TERMS_NULL', len(terms) == 18 and all(not r['value_rub'] and not r['full_money_delta_rub'] and r['value_status'] == 'UNKNOWN' for r in terms), 18)
    eq('REAL_BUDGET_UNKNOWN', obj('runs/economics/summary.json')['real_full_budget'], 'UNKNOWN')
    table('independent_capacity_fixtures.csv', econ)

    counterexamples = [
        dict(id='C01_INDEPENDENT_RANGES_INVALID', inputs=dict(M=60, T=45, x=135, y=120),
             calculation='Both projection ranges contain the point; SOUTH turn=45+y-x=30<45', rejected=True, production_defect=False),
        dict(id='C01_CONTINUOUS_BOUNDARY', inputs=dict(M=67.5, T=45, x=127.5, y=127.5),
             calculation='2M+T=180 feasible; M=67.51 implies180.02>180 infeasible; exact real-valued algebra', rejected=False, production_defect=False),
        dict(id='C07_ADVANCE_ONE_MINUTE_SHORT', inputs=dict(T=45, L=180, advance=174),
             calculation='delta=355; deadline slack180; required175;174 returns1min late', rejected=True, production_defect=False),
        dict(id='C07_NEXT_TURN_ALREADY_NETTED', inputs=dict(gross_slack=225, next_turn=45),
             calculation='L=180; required175. Treating gross225 as L gives130, misses net deadline45min', rejected=True, production_defect=False),
        dict(id='C14_PROPERTY_POLICY_SUM', inputs=dict(property_policy_pass_rows=sum(r['date_matched_property_rows'] for r in summaries)),
             calculation='66 row-policy passes collapse to11 distinct date/stay requests across all alternatives; no observed customers', rejected=True, production_defect=False),
        dict(id='C14_UNKNOWN_IS_NOT_ZERO', inputs=dict(checkout='2026-12-25', capture_end='2026-12-24'),
             calculation='No captured return on/after checkout; UNKNOWN service, inventory and demand; no zero-sales claim', rejected=True, production_defect=False),
        dict(id='CAPACITY_K500K', inputs=dict(local_load=80, seats=100, q=34),
             calculation='80+34=114>100 on each used leg despite positive10000RUB arithmetic threshold contribution', rejected=True, production_defect=False),
        dict(id='OVERLAPPING_ALTERNATIVES', inputs=dict(residual=20, alternative_A=20, alternative_B=20),
             calculation='Separate feasible alternatives need40>20 seats if combined; shared pool20 also prohibits40 distinct journeys', rejected=True, production_defect=False),
        dict(id='K_DEPENDS_ON_Q', inputs=dict(K0=300000, extra_cost_per_q=1000),
             calculation='2*7500*q-(300000+1000*q)>=0 needs22/direction; fixed-K q20 loses20000 and q22 exceeds residual20', rejected=True, production_defect=False),
        dict(id='FARE_PER_LEG', inputs=dict(q=20, fare=8000, legs_per_direction=2),
             calculation='C01 correct revenue2*20*8000=320000; multiplying by2legs creates640000; seats still80segments', rejected=True, production_defect=False),
        dict(id='DONOR_REVENUE_AND_MARGIN', inputs=dict(lost_revenue=100000, avoided_passenger_cost=20000),
             calculation='Lost contribution80000 once; subtracting100000+80000 duplicates loss by100000', rejected=True, production_defect=False),
        dict(id='PERSON_DAY_TIMES_NIGHTS', inputs=dict(tariff=7760, nights=7),
             calculation='54320 is not an admitted stay quote: billed days, tax inclusion, late admission and inventory UNKNOWN', rejected=True, production_defect=False),
    ]
    # Independently execute the numeric mutation rejection predicates.
    mutation_predicates = [45+120-135 < 45, 2*67.5+45 == 180, 2*67.51+45 > 180,
                           355-174 > 180, 355-130-180 == 45, 80+34 > 100,
                           20+20 > 20, 2*7500*20-(300000+1000*20) == -20000,
                           math.ceil(300000/14000) == 22, 2*20*8000 == 320000,
                           sum(r['date_matched_property_rows'] for r in summaries) == 66,
                           len({r['distinct_date_stay_id'] for r in policies if r['gate'] == 'DATE_MATCH_ONLY'}) == 11]
    check('INDEPENDENT_COUNTEREXAMPLES', all(mutation_predicates), dict(predicates=len(mutation_predicates), counterexamples=len(counterexamples)))
    save('counterexamples.json', counterexamples)

    hold = obj('inputs/source_join_review/findings.json')
    check('OLD_SVX_HOLD_PRESERVED', hold['verdict'] == 'CHANGES' and
          any(r['id'] == 'SJR-P2-001' and r['status'] == 'OPEN' for r in hold['findings']) and
          any(r['status'] == 'INHERITED_HOLD_NOT_REPAIRED_HERE' for r in obj('findings.json')['findings']),
          'Read exact original lineage HOLD only; no independent source acceptance; root corrections outside scope')
    save('claim_scope.json', dict(
        review_id='FRONTIER_REVIEW', not_review_id='MR11',
        arithmetic_calendar_conservation='PERSONALLY_RECOMPUTED_FROM_EXACT_FROZEN_INPUTS',
        author_code_executed=False, supplied_self_checks_counted_as_personal=False,
        source_support='UNKNOWN_NOT_REVIEWED; Git hashes are not primary-source support',
        market='UNKNOWN', full_budget='UNKNOWN', operating_acceptance='UNKNOWN',
        actual_sales=None, actual_margin=None, actual_K_q=None, actual_free_resource=None,
        MOW='Metropolitan code, not an airport or an admitted physical leg',
        fleet='Case restriction earliest H2_2027; no delivery/free-tail guarantee for2027/2028',
        final_network='Pilots do not establish jointly allocated8-12routes',
        old_SVX_primary_lineage='SJR-P2-001 HOLD in exact original retained',
        root_corrections='OUTSIDE_THIS_REVIEW; no input upgrade',
        no_external_PASS_inherited=True, no_new_research=True))
    failures = [r['check_id'] for r in CHECKS if r['status'] == 'FAIL']
    save('checks.json', dict(review_id='FRONTIER_REVIEW', input_commit=PIN, checks=CHECKS,
                             pass_count=len(CHECKS)-len(failures), fail_count=len(failures), failed_checks=failures,
                             author_self_checks_not_executed=True, acceptance_scope='INDEPENDENT_OFFLINE_ARITHMETIC_CALENDAR_CONSERVATION_ONLY'))
    save('source_manifest.json', dict(review_id='FRONTIER_REVIEW', input_commit=PIN, root_commit=BASE,
             source_cutoff_msk='2026-11-10T08:15:00+03:00', reads=list(READS.values()),
             raw_copied=False, network_research=False, author_code_executed=False,
             source_acceptance='NOT_ESTABLISHED', grain_note='CSV row units recorded in upstream manifest; derived table grain in table_dictionary.csv'))
    print(json.dumps(dict(checks=len(CHECKS), passed=len(CHECKS)-len(failures), failed=failures,
                          git_blobs=len(READS), c01_profiles=len(bounds), c07_cases=len(c07_cases),
                          c14_distinct=[r['date_matched_distinct'] for r in summaries], fixtures=len(econ))))
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
