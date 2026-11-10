#!/usr/bin/env python3
"""MR10: exact-blob independent joins, time oracle, admission and preservation.

Only stdlib; no network, author main, raw downloads or writes outside this folder.
Author overlay functions are used only for the separately labelled bounded replay.
"""
import ast
import collections
import csv
import hashlib
import io
import json
import math
import pathlib
import subprocess
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

OUT = pathlib.Path(__file__).resolve().parent
P = 'context/23_night_run_20261110/'
PREP = '47de3dfb3d20c29232396f5a28c664a97630b3d9'
A = 'f1774e1f66a9483fb618ca6003abd9dc4d8563e1'
B = '87ee52de15c2bdf396d9c06ba600fd413d5ab4a8'
PRIMARY = '17b4f348f15ea8695688d9435933cb4965568408'
BRIDGE = 'abc09bbb8e62d3513749b60b252d4521997acfc3'
AUTHOR = '93fa5cf4a10ab67e05c93d19fc5375fc58ef9299'
ORIGINAL = 'afadee35ebeefe54a05bdfc5b3e224a370f90e0a'
SJR = '944b16ac2dcde846e29dac2d47e11e5143f9fc2b'
CKR = 'af96da977becc161eac132f587e1fd3c4d6918a3'
AP = P + 'primary_lineage_correction/'
BP = P + 'cost_kover_timebase_correction/'
OP = P + 'cost_kover/'
PP = P + 'primary_evidence/'
CACHE, SOURCES, CHECKS = {}, {}, []


def sha(b):
    return hashlib.sha256(b).hexdigest()


def blob(commit, path, grain='code / metadata / receipt'):
    key = commit, path
    if key not in CACHE:
        CACHE[key] = subprocess.check_output(['git', 'show', commit + ':' + path])
        SOURCES[key] = dict(source_commit=commit, path=path, sha256=sha(CACHE[key]),
                            bytes=len(CACHE[key]), grain=grain)
    return CACHE[key]


def js(commit, path):
    return json.loads(blob(commit, path))


def rows(commit, path, grain='CSV row; columns define units'):
    return list(csv.DictReader(io.StringIO(blob(commit, path, grain).decode('utf-8-sig'))))


def check(name, ok, evidence=None, section='independent'):
    CHECKS.append(dict(id=name, status='PASS' if ok else 'FAIL', section=section,
                       evidence=evidence))


def equal(a, b):
    if a is None or b is None:
        return a == b
    if str(a) == str(b):
        return True
    try:
        return math.isclose(float(a), float(b), abs_tol=1e-6, rel_tol=1e-12)
    except (ValueError, TypeError):
        return False


def write_json(name, x):
    (OUT / name).write_text(json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def write_csv(name, rr):
    rr = list(rr)
    with (OUT / name).open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, list(dict.fromkeys(k for r in rr for k in r)), lineterminator='\n')
        w.writeheader()
        w.writerows(rr)


def verify_manifest(commit, prefix):
    m = js(commit, prefix + 'output_manifest.json')
    result = []
    for f in m['files']:
        data = blob(commit, prefix + f['path'])
        result.append(dict(path=f['path'], bytes_match=len(data) == f['bytes'],
                           sha256_match=sha(data) == f['sha256']))
    handoff = js(commit, prefix + 'handoff.json')
    check(prefix + 'manifest', all(r['bytes_match'] and r['sha256_match'] for r in result)
          and handoff['manifest_sha256'] == sha(blob(commit, prefix + 'output_manifest.json')),
          result, 'integrity_only')
    return result


def check_cells(name, old, new, line_field):
    mismatches = [(i + 2, k, r[k], s.get(k)) for i, (r, s) in enumerate(zip(old, new))
                  for k in r if r[k] != s.get(k)]
    check(name, len(old) == len(new) and not mismatches
          and all(s[line_field] == str(i + 2) for i, s in enumerate(new)),
          dict(rows=len(old), columns=len(old[0]), cells=len(old) * len(old[0]),
               added_columns=[k for k in new[0] if k not in old[0]], mismatches=mismatches))


def review_a():
    registry = rows(A, AP + 'source_registry.csv', 'source_id × current snapshot')
    dated = rows(A, AP + 'dated_evidence.csv', 'dated published directional service')
    mapping = rows(A, AP + 'candidate_endpoint_mapping.csv', 'card × endpoint candidate context link')
    bindings = rows(A, AP + 'card_snapshot_bindings.csv', 'one current snapshot binding per affected card')
    historical = rows(A, AP + 'historical_snapshot_registry.csv')
    old_reg = rows(PRIMARY, PP + 'source_registry.csv')
    old_dated = rows(PRIMARY, PP + 'dated_evidence.csv')
    cards = rows(PRIMARY, PP + 'route_product_cards.csv')
    old_mapping = rows(BRIDGE, P + 'data_bridge/candidate_addendum_primary17b/candidate_endpoint_mapping.csv')
    current_receipts = js(AUTHOR, 'context/17_aircraft_route_review/evidence/sources.json')
    old_receipts = js(AUTHOR, 'context/12_network_economics/sources.json')
    upstream = rows(AUTHOR, 'context/17_aircraft_route_review/evidence/published_service_facts.csv')
    targets = {'svx_schedule', 'svx_schedule_arr'}
    by_id = {r['source_id']: r for r in registry}
    old_by_id = {r['source_id']: r for r in old_reg}
    receipts = {r['id']: r for r in current_receipts}
    previous = {r['id']: r for r in old_receipts}
    legacy = {r['source_id']: r for r in historical}
    check('A_registry_cardinality', len(registry) == len(old_reg) == len(by_id) == 48)
    check_cells('A_all_dated_cells_preserved', old_dated, dated, 'original_csv_line')
    check_cells('A_all_mapping_cells_preserved', old_mapping, mapping, 'original_mapping_csv_line')
    affected = [r for r in dated if r['source_id'] in targets]
    mismatched = [r for r in old_dated if r['html_sha256'] != old_by_id[r['source_id']]['raw_sha256']]
    check('A_original_mismatch_reproduced', len(mismatched) == 129 and
          set(r['source_id'] for r in mismatched) == targets,
          dict(affected_rows=len(mismatched), by_source=dict(collections.Counter(r['source_id'] for r in mismatched))))
    literal = []
    for sid in sorted(targets):
        r, c, prev, h = by_id[sid], receipts[sid], previous[sid], legacy[sid]
        check('A_receipt_identity_' + sid,
              r['url'] == c['url'] == prev['url'] and r['raw_sha256'] == c['sha256']
              and r['captured_at_utc'] == c['accessed'] == '2026-11-09'
              and r['http_status'] == str(c['http']) == '200'
              and r['receipt_commit'] == AUTHOR
              and r['receipt_path'] == 'context/17_aircraft_route_review/evidence/sources.json'
              and c['status'] == 'PRIMARY_WINTER_TIMETABLE_PARSED'
              and r['access_status'] == old_by_id[sid]['access_status'] == 'REUSED_SOURCE_HASH_FROM_MANIFEST'
              and r['claim_status'] == 'PLANNED_NOT_EXECUTED'
              and r['source_snapshot_id'] == sid + '@sha256:' + c['sha256'])
        check('A_null_new_size_' + sid, 'bytes' not in c and r['bytes'] == ''
              and h['bytes'] == str(prev['bytes']) and h['bytes'] != r['bytes'])
        check('A_historical_separation_' + sid,
              h['raw_sha256'] == prev['sha256'] == old_by_id[sid]['raw_sha256']
              and h['captured_at_utc'] == prev['accessed'] == '2026-11-08'
              and h['source_snapshot_id'] != r['source_snapshot_id']
              and h['receipt_path'] == 'context/12_network_economics/sources.json'
              and h['source_commit'] == AUTHOR
              and h['use_status'] == 'HISTORICAL_SNAPSHOT_NOT_SUPPORT_FOR_CONTEXT17_ROWS')
        example = next(r for r in affected if r['source_id'] == sid)
        literal.append(dict(source_id=sid, context17_receipt=c, context12_receipt={k: prev[k] for k in ['id', 'url', 'accessed', 'sha256', 'bytes']},
                            corrected_registry=r, representative_dated_row=example))
    allowed = {'captured_at_utc', 'raw_sha256', 'bytes', 'http_status', 'raw_local_path', 'limits'}
    reg_changes = [(r['source_id'], k) for r in registry for k in old_by_id[r['source_id']]
                   if r[k] != old_by_id[r['source_id']][k]]
    check('A_only_target_registry_fields_change', all(sid in targets and k in allowed for sid, k in reg_changes), reg_changes)
    check('A_complete_snapshot_fk', len(dated) == 209 and all(
        r['source_snapshot_id'] == by_id[r['source_id']]['source_snapshot_id']
        == r['source_id'] + '@sha256:' + r['html_sha256'] for r in dated))
    check('A_full_snapshot_identity_unique', len({r['source_snapshot_id'] for r in registry + historical}) == 50)
    projected = []
    fields = ['origin', 'destination', 'date', 'departure_local', 'arrival_local', 'carrier', 'flight', 'aircraft', 'source_url', 'period', 'html_sha256', 'evidence_kind']
    for r in affected:
        u = upstream[int(r['source_row']) - 2]
        matches = all(u[k] == r[k] for k in fields)
        matches = matches and u['source'] == r['source_id'] and u['block_minutes'] == r['duration_minutes']
        matches = matches and u['accessed'] == by_id[r['source_id']]['captured_at_utc']
        projected.append(dict(original_csv_line=r['original_csv_line'], source_id=r['source_id'],
                               upstream_csv_line=r['source_row'], source_snapshot_id=r['source_snapshot_id'],
                               literal_fields_match=matches))
    check('A_independent_upstream_row_join', len(projected) == 129 and all(r['literal_fields_match'] for r in projected))
    affected_cards = [r for r in cards if targets.intersection(r['source_ids'].split(';'))]
    card_by = {r['card_id']: r for r in cards}
    binding_by = {r['card_id']: r for r in bindings}
    check('A_28_card_bindings_exact', len(bindings) == len(binding_by) == len(affected_cards) == 28
          and set(binding_by) == {r['card_id'] for r in affected_cards}
          and all(b['source_id'] == card_by[b['card_id']]['source_ids'] and
                  b['raw_sha256'] == card_by[b['card_id']]['raw_sha256'] == by_id[b['source_id']]['raw_sha256']
                  and b['clock_consensus_status'] == card_by[b['card_id']]['clock_consensus_status']
                  and b['source_snapshot_id'] == by_id[b['source_id']]['source_snapshot_id']
                  and b['original_commit'] == PRIMARY and b['original_path'] == PP + 'route_product_cards.csv'
                  and b['other_acceptance'] == 'INHERITED_SCOPE_ONLY; NO_CLOCK_OR_SUPPLY_UPGRADE' for b in bindings))
    affected_mapping = [r for r in mapping if r['card_id'] in binding_by]
    counts = dict(collections.Counter(r['status'] for r in affected_mapping))
    check('A_58_mapping_fk', len(affected_mapping) == 58 and all(
        r['source_snapshot_id'] == binding_by[r['card_id']]['source_snapshot_id']
        and r['raw_sha256'] == binding_by[r['card_id']]['raw_sha256']
        and r['source_ids'] == binding_by[r['card_id']]['source_id']
        and card_by[r['card_id']] == cards[int(r['source_card_row']) - 2] for r in affected_mapping), counts)
    check('A_hold_context_and_no_match_retained', counts == {
        'HOLD_EXACT_CLOCK; SUPPLY_CONTEXT_ONLY': 6, 'CONTEXT_CANDIDATE_ONLY': 42, 'NO_BASELINE_ENDPOINT_MATCH': 10}
        and all(r['numerical_uplift'] == 'NONE' and r['model_input_changed'] == 'False'
                and r['seats'] == r['observed_final_OD'] == r['net_fare'] == '' for r in affected_mapping))
    check('A_no_fabricated_unaffected_mapping_fk', all(r['source_snapshot_id'] == '' for r in mapping if r['card_id'] not in binding_by))
    # A counterexample to source_id-only joins: exact URL/id is unchanged, raw hash is not.
    write_json('lineage_receipts.json', literal)
    write_csv('independent_lineage_join.csv', projected)
    write_csv('held_clock_mappings.csv', [r for r in affected_mapping if r['status'].startswith('HOLD')])
    lock = js(A, AP + 'source_lock.json')
    for item in lock['correction_inputs'] + lock['original_package_source_locks']:
        data = blob(item['source_commit'], item['path'])
        check('A_input_lock:' + item['path'], sha(data) == item['sha256'] and len(data) == item['bytes'], section='integrity_only')
    check('A_original_manifest_retained', js(A, AP + 'unchanged_original_outputs.json')['files'] == js(PRIMARY, PP + 'manifest.json')['files'], section='integrity_only')
    return dict(affected_rows=len(affected), original_dated_rows=len(dated), original_mapping_rows=len(mapping),
                affected_cards=len(bindings), affected_mappings=len(affected_mapping), mapping_statuses=counts)


def review_b():
    definition = js(ORIGINAL, OP + 'scenario_definitions.json')
    flights = rows(ORIGINAL, OP + 'inputs/tsiri_flights.csv', 'dated physical leg; absolute minutes from period start UTC')
    sales = rows(ORIGINAL, OP + 'inputs/tsiri_sales.csv', 'scenario itinerary; one endpoint fare and one seat per linked leg')
    caps = rows(ORIGINAL, OP + 'inputs/tsiri_capacity.csv')
    baseline = rows(ORIGINAL, OP + 'inputs/tsiri_comparison.csv')
    old_summary = rows(ORIGINAL, OP + 'scenario_summary.csv')
    old_physical = rows(ORIGINAL, OP + 'physical_leg_status.csv')
    old_journeys = rows(ORIGINAL, OP + 'affected_journeys.csv')
    old_cash = rows(ORIGINAL, OP + 'cost_cash_bridge.csv')
    summary = rows(B, BP + 'scenario_summary.csv')
    physical = rows(B, BP + 'physical_leg_status.csv')
    journeys = rows(B, BP + 'affected_journeys.csv')
    cash = rows(B, BP + 'cash_fixture.csv')
    projection = rows(B, BP + 'timestamp_projection.csv')
    conflicts = rows(B, BP + 'rotation_conflicts.csv')
    selected = [r for r in flights if r['profile'] == definition['profile'] and r['network'] in definition['networks']]
    epoch = datetime.fromisoformat(definition['period_start']).replace(tzinfo=timezone.utc)
    epoch_seconds = int(epoch.timestamp())
    horizon = datetime.fromisoformat(definition['period_end']).replace(tzinfo=timezone.utc) + timedelta(days=1)

    def instant(r, event, delay=0):
        seconds = Decimal(r[event + '_utc_minute']) * 60 + Decimal(str(delay)) * 60
        return datetime.fromtimestamp(epoch_seconds + float(seconds), timezone.utc)

    def old_instant(r, event):
        return datetime.fromisoformat(r['date']).replace(tzinfo=timezone.utc) + timedelta(minutes=float(r[event + '_utc_minute']))

    def hits(r, episode, delay=0):
        start = datetime.fromisoformat(episode['start_utc'])
        end = datetime.fromisoformat(episode['end_utc_exclusive'])
        if end < start:
            raise ValueError('negative interval')
        events = [('origin', 'departure'), ('destination', 'arrival')]
        return any(r[endpoint] == episode['airport'] and start <= instant(r, event, delay) < end for endpoint, event in events)

    author_code = blob(AUTHOR, 'scripts/build_team_comparison.py').decode()
    check('B_author_epoch_literal', "WEEK = '2026-12-07'" in author_code
          and 'departure_utc_minute=(day-1)*1440+start' in author_code
          and 'arrival_utc_minute=(day-1)*1440+start+v' in author_code,
          dict(commit=AUTHOR, path='scripts/build_team_comparison.py', lines=[28, 363, 364, 365]))
    by_flight = {r['id']: r for r in selected}
    check('B_66_leg_cardinality', len(selected) == len(by_flight) == 66,
          dict(networks=dict(collections.Counter(r['network'] for r in selected)), dates=dict(collections.Counter(r['date'] for r in selected))))
    independent_times = []
    for r in selected:
        for event in ['departure', 'arrival']:
            old, new = old_instant(r, event), instant(r, event)
            independent_times.append(dict(network=r['network'], flight_id=r['id'], source_date=r['date'], event=event,
                                          absolute_minute=r[event + '_utc_minute'], expected_utc=new.isoformat(),
                                          expected_old_utc=old.isoformat(), old_minus_corrected_minutes=(old-new).total_seconds()/60))
    expected_times = {(r['flight_id'], r['event']): r for r in independent_times}
    check('B_132_timestamp_projection', len(projection) == len(expected_times) == 132
          and {(r['flight_id'], r['event']) for r in projection} == set(expected_times)
          and all(r['corrected_utc'] == expected_times[r['flight_id'], r['event']]['expected_utc']
                  and r['old_utc'] == expected_times[r['flight_id'], r['event']]['expected_old_utc']
                  and equal(r['old_minus_corrected_minutes'], expected_times[r['flight_id'], r['event']]['old_minus_corrected_minutes'])
                  for r in projection))
    check('B_original_70_wrong_events', sum(r['old_minus_corrected_minutes'] != 0 for r in independent_times) == 70)
    wrong_original = sum(r['scheduled_departure_utc'] != instant(by_flight[r['flight_id']], 'departure').isoformat()
                         or r['scheduled_arrival_utc'] != instant(by_flight[r['flight_id']], 'arrival').isoformat() for r in old_physical)
    check('B_original_350_wrong_physical_rows', wrong_original == 350, wrong_original)
    check('B_all_660_physical_UTC_pairs', len(physical) == len(old_physical) == 660 and all(
        r['scheduled_departure_utc'] == instant(by_flight[r['flight_id']], 'departure').isoformat()
        and r['scheduled_arrival_utc'] == instant(by_flight[r['flight_id']], 'arrival').isoformat()
        and (not r['conditional_actual_departure_utc'] or r['conditional_actual_departure_utc'] == instant(by_flight[r['flight_id']], 'departure', 1440).isoformat())
        and (not r['conditional_actual_arrival_utc'] or r['conditional_actual_arrival_utc'] == instant(by_flight[r['flight_id']], 'arrival', 1440).isoformat()) for r in physical))
    example = by_flight['ROUTE_INPUTS_UPPER_100_H_UFA_8_028']
    check('B_mandatory_1885', example['date'] == '2026-12-08' and float(example['departure_utc_minute']) == 1885
          and instant(example, 'departure').isoformat() == '2026-12-08T07:25:00+00:00')
    day2 = dict(definition['episode'], start_utc='2026-12-08T00:00:00+00:00', end_utc_exclusive='2026-12-09T00:00:00+00:00')
    u8 = [r for r in selected if r['network'] == 'H_UFA_8']
    old_hits = [r['id'] for r in u8 if any(r[k] == 'UFA' and datetime.fromisoformat(day2['start_utc']) <= old_instant(r,e) < datetime.fromisoformat(day2['end_utc_exclusive']) for k,e in [('origin','departure'),('destination','arrival')])]
    new_hits = [r['id'] for r in u8 if hits(r, day2)]
    check('B_day2_0_to_16', len(old_hits) == 0 and len(new_hits) == 16, dict(old=old_hits, corrected=new_hits))
    check('B_all_selected_durations_and_horizon', all(instant(r,'arrival') - instant(r,'departure') == timedelta(minutes=float(r['block_minutes']))
          and epoch <= instant(r,'departure') < instant(r,'arrival') < horizon for r in selected))
    write_csv('independent_timestamps.csv', independent_times)

    # Separate oracle fixtures use absolute offsets and event airport identity.
    fixture = dict(example, origin='UFA', destination='XXX', date='2099-01-01')
    fixture_results = []
    fixtures = [('start_included',1440,1500,True), ('end_excluded',2880,2940,False),
                ('before_start_excluded',1439,1500,False), ('last_minute_included',2879,2940,True)]
    for name, departure, arrival, expected in fixtures:
        r = dict(fixture, departure_utc_minute=str(departure), arrival_utc_minute=str(arrival))
        fixture_results.append(dict(name=name, expected=expected, actual=hits(r,day2)))
    arrival_fixture = dict(fixture, origin='XXX', destination='UFA', departure_utc_minute='1435', arrival_utc_minute='1495')
    fixture_results.append(dict(name='arrival_event_at_restricted_airport_after_rollover',expected=True,actual=hits(arrival_fixture,day2)))
    check('B_half_open_event_oracle', all(r['actual'] == r['expected'] for r in fixture_results), fixture_results)
    check('B_other_airport_not_restricted', not hits(dict(arrival_fixture, destination='YYY'),day2))
    check('B_rollover_no_modulo', instant(arrival_fixture,'departure').date().isoformat() == '2026-12-07'
          and instant(arrival_fixture,'arrival').date().isoformat() == '2026-12-08')
    ufa_time = instant(example,'departure').astimezone(ZoneInfo('Asia/Yekaterinburg'))
    oms_time = instant(example,'departure').astimezone(ZoneInfo('Asia/Omsk'))
    local_window = dict(day2,start_utc='2026-12-08T05:00:00+05:00',end_utc_exclusive='2026-12-09T05:00:00+05:00')
    check('B_timezone_equivalent_windows', [r['id'] for r in u8 if hits(r,local_window)] == new_hits
          and ufa_time.isoformat() == '2026-12-08T12:25:00+05:00'
          and oms_time.isoformat() == '2026-12-08T13:25:00+06:00',
          dict(utc=instant(example,'departure').isoformat(), UFA=ufa_time.isoformat(), OMS_same_instant=oms_time.isoformat()))

    # Independent adjacency algorithm checks each planning label, with original
    # stable ordering when departure ties occur. It does not search alternative fleets.
    independent_conflicts = []
    conflicts_by_network = {}
    for network in definition['networks']:
        ll = [r for r in selected if r['network'] == network]
        touched = {r['id'] for r in ll if hits(r,definition['episode'])}
        grouped = collections.defaultdict(list)
        for r in ll:
            grouped[r['aircraft']].append(r)
        found = []
        for tail, seq in grouped.items():
            shifted = sorted(seq, key=lambda r:instant(r,'departure',1440 if r['id'] in touched else 0))
            for left,right in zip(shifted,shifted[1:]):
                ld = 1440 if left['id'] in touched else 0
                rd = 1440 if right['id'] in touched else 0
                gap = (instant(right,'departure',rd) - instant(left,'arrival',ld)).total_seconds()/60
                location_bad = left['destination'] != right['origin']
                if gap < 45 or location_bad:
                    found.append(dict(network=network,planning_label=tail,left=left['id'],right=right['id'],
                                      left_arrival_utc=instant(left,'arrival',ld).isoformat(),right_departure_utc=instant(right,'departure',rd).isoformat(),
                                      gap_minutes=gap,location_mismatch=location_bad))
        conflicts_by_network[network] = len(found)
        independent_conflicts.extend(found)
    expected_conflicts = {(r['network'],s,r['planning_label'],r['left'],r['right']) for r in independent_conflicts for s in definition['author_scenarios']}
    observed_conflicts = {(r['network'],r['scenario'],r['planning_label'],r['left'],r['right']) for r in conflicts}
    check('B_conflict_sets_exact', len(conflicts) == len(observed_conflicts) == len(expected_conflicts) == 68 and observed_conflicts == expected_conflicts,
          conflicts_by_network)
    check('B_UFA8_23_UFA4_11_each_scenario', conflicts_by_network == {'H_UFA_8':23,'H_UFA_4':11,'D_pilot':0,'D_case':0})
    check('B_planning_labels_retained_no_real_tail', all(r['planning_aircraft_label'] == by_flight[r['flight_id']]['aircraft'] and r['actual_tail'] == '' for r in physical))
    write_csv('independent_rotation_conflicts.csv', independent_conflicts)

    key = lambda r:(r['network'],r['author_scenario'],r['scenario_id'])
    summaries = {key(r):r for r in summary}
    old_summaries = {key(r):r for r in old_summary}
    check('B_40_summary_keys', len(summary) == len(summaries) == 40 and set(summaries) == set(old_summaries))
    physical_groups, journey_groups, cash_groups = (collections.defaultdict(list) for _ in range(3))
    for rr,group in [(physical,physical_groups),(journeys,journey_groups),(cash,cash_groups)]:
        for r in rr:
            group[key(r)].append(r)
    held_keys = {k for k,r in summaries.items() if r['value_status'] == 'HOLD_DELAY_COMPLETION_UNRESOLVED_ROTATION'}
    expected_held = {(n,s,'delay_bank_next_day_fare_retained') for n in ['H_UFA_8','H_UFA_4'] for s in definition['author_scenarios']}
    check('B_only_4_unresolved_cases_held', held_keys == expected_held)
    admitted_fields = ['remaining_endpoint_journeys','unserved_endpoint_journeys','unserved_segment_allocations',
                       'overlay_delta_before_unknown_rub','contribution_after_overlay_before_unknown_rub','additional_cash_peak_timing_stress_rub']
    journey_admitted = ['conditionally_served_endpoint_journeys','unserved_endpoint_journeys','retained_net_fare_rub']
    check('B_summary_admission_null', all(r[f] == '' and equal(r['hypothetical_'+f+'_if_recovered'],old_summaries[k][f])
          for k,r in summaries.items() if k in held_keys for f in admitted_fields))
    check('B_held_journey_admission_null', all(r[f] == '' and r['hypothetical_'+f+'_if_recovered'] != ''
          and r['value_status'] == 'HOLD_DELAY_COMPLETION_UNRESOLVED_ROTATION'
          for k in held_keys for r in journey_groups[k] for f in journey_admitted))
    check('B_physical_allocation_status_held', all(r['value_status'] == 'HOLD_DELAY_COMPLETION_UNRESOLVED_ROTATION' for k in held_keys for r in physical_groups[k]),
          'remaining_occupied/capacity are retained candidate allocations under HOLD, not admitted service')
    check('B_delay_cash_fixture_explicitly_hypothetical', all(r['value_status'] == 'HYPOTHETICAL_COMPLETION_CASH_NOT_AVAILABLE_SCHEDULE' for k in held_keys for r in cash_groups[k]),
          'Numeric delta fields are fixture algebra. There are no admitted cash columns in cash_fixture; summary admitted peak is NULL.')
    check('B_no_schedule_or_full_budget_promotion', all(r['usable_as_served_schedule'] == 'False' and r['actual_operational_readiness'] == 'UNKNOWN'
          and r['full_budget_profit_rub'] == r['actual_full_cash_peak_rub'] == '' for r in summary))
    check('B_correction_and_parent_provenance', all(r['input_set_id'] == 'MR02-TIMEBASE-CORRECTION:afadee35'
          and r['parent_input_set_id'] == definition['input_set_id'] and r['run_id'] == 'MR02-timebase-correction-v1'
          and r['source_commit'] == AUTHOR and r['source_overlay_commit'] == ORIGINAL
          for r in summary+physical+journeys+cash),
          dict(correction_commit=B, original_overlay_commit=ORIGINAL, author_source_commit=AUTHOR,
               note='timebase_correction_source_commit is the original overlay input SHA; exact correction identity is B + input_set_id/run_id'))

    # Independently reconstruct affected unions, segment allocations and seat use.
    conservation = []
    for k,s in summaries.items():
        network,scenario,policy_id = k
        policy = next(p for p in definition['scenarios'] if p['id'] == policy_id)
        ll = [r for r in selected if r['network'] == network]
        ss = [(line,r) for line,r in enumerate(sales,2) if r['profile'] == definition['profile'] and r['network'] == network and r['scenario'] == scenario]
        touched = {r['id'] for r in ll if policy['episode_active'] and hits(r,definition['episode'])}
        impacted = [(line,r) for line,r in ss if touched.intersection(r['flight_ids'].split(';'))]
        cancelled = touched if policy['action'] == 'cancel' else set()
        lost = [(line,r) for line,r in ss if cancelled.intersection(r['flight_ids'].split(';'))]
        affected_ids = {str(line) for line,r in impacted}
        observed_ids = {r['source_csv_line'] for r in journey_groups[k]}
        q = sum(float(r['sold_journeys']) for _,r in impacted)
        lost_q = sum(float(r['sold_journeys']) for _,r in lost)
        lost_segs = sum(float(r['sold_journeys']) * len(r['flight_ids'].split(';')) for _,r in lost)
        remaining_q = sum(float(r['sold_journeys']) for _,r in ss) - lost_q
        used = collections.Counter()
        for _,r in ss:
            if not cancelled.intersection(r['flight_ids'].split(';')):
                for fid in r['flight_ids'].split(';'):
                    used[fid] += float(r['sold_journeys'])
        f = lambda field:s['hypothetical_'+field+'_if_recovered'] if k in held_keys and field in admitted_fields else s[field]
        ok = affected_ids == observed_ids and len(journey_groups[k]) == len(affected_ids)
        ok = ok and int(s['affected_physical_legs']) == len(touched) and equal(s['affected_endpoint_journeys'],q)
        ok = ok and equal(f('unserved_endpoint_journeys'),lost_q) and equal(f('unserved_segment_allocations'),lost_segs) and equal(f('remaining_endpoint_journeys'),remaining_q)
        ok = ok and all(equal(r['remaining_occupied'],used[r['flight_id']]) and float(r['remaining_occupied']) <= float(r['remaining_capacity']) + 1e-6 for r in physical_groups[k])
        for r in journey_groups[k]:
            source = sales[int(r['source_csv_line'])-2]
            ok = ok and r['flight_ids'] == source['flight_ids'] and r['journey_id'] == 'tsiri-sales-line-'+r['source_csv_line']
            ok = ok and int(r['affected_leg_count']) == len(touched.intersection(source['flight_ids'].split(';')))
            ok = ok and equal(r['affected_endpoint_journeys'],source['sold_journeys'])
        conservation.append(dict(network=network,author_scenario=scenario,scenario_id=policy_id,
                                 affected_legs=len(touched),affected_journey_rows=len(impacted),
                                 affected_endpoint_journeys=q,unserved_if_policy_completed=lost_q,
                                 unserved_segments_if_policy_completed=lost_segs,
                                 admitted=k not in held_keys,identities_match=ok))
    check('B_independent_conservation_and_affected_sets', all(r['identities_match'] for r in conservation),
          dict(summary_groups=len(conservation),physical_rows=len(physical),journey_rows=len(journeys),cash_rows=len(cash)))
    write_csv('independent_conservation.csv',conservation)

    # Exact original-cell preservation outside time/status/provenance and the
    # explicitly gated fields. Day1 cancellation arithmetic is byte-cell equal.
    preservation = []
    exclusions = {'input_set_id','run_id','acceptance_scope','value_status','template_rotation_status',
                  'scheduled_departure_utc','scheduled_arrival_utc','conditional_actual_departure_utc','conditional_actual_arrival_utc'}
    for name,old,new in [('summary',old_summary,summary),('physical',old_physical,physical),('journeys',old_journeys,journeys),('cash',old_cash,cash)]:
        differences = []
        for i,(r,s) in enumerate(zip(old,new),2):
            gated = set(admitted_fields if name=='summary' else journey_admitted if name=='journeys' else []) if key(s) in held_keys else set()
            for f in r:
                if f not in exclusions|gated and r[f] != s.get(f):
                    differences.append([i,f,r[f],s.get(f)])
        preservation.append(dict(table=name,original_rows=len(old),corrected_rows=len(new),
                                 unchanged_nonexcluded_cells=not differences,differences=differences))
    check('B_unaffected_original_values_preserved', all(r['original_rows']==r['corrected_rows'] and r['unchanged_nonexcluded_cells'] for r in preservation),preservation)
    check('B_cancel_day1_and_no_kover_summary_values_identical', all(old_summaries[k][f] == s[f]
          for k,s in summaries.items() if k not in held_keys for f in old_summaries[k] if f not in exclusions))
    # Original no-kover exports remain exact input blobs; the correction contains
    # no replacement input files and its lock hashes are verified below.
    original_baseline = js(ORIGINAL,OP+'source_manifest.json')
    input_exports = {'tsiri_flights.csv','tsiri_sales.csv','tsiri_capacity.csv','tsiri_comparison.csv',
                     'tsiri_inputs.json','tsiri_overrides.json'}
    byte_preservation = []
    for r in original_baseline['sources']:
        if r['id'] in input_exports:
            copied = blob(ORIGINAL,OP+r['local_path'])
            upstream = blob(r['source_commit'],r['source_path'],r['grain'])
            byte_preservation.append(dict(id=r['id'],source_commit=r['source_commit'],source_path=r['source_path'],
                                           original_overlay_input_sha256=sha(copied),author_export_sha256=sha(upstream),
                                           manifest_sha256=r['sha256'],bytes_identical=copied==upstream))
    check('B_frozen_no_kover_input_bytes_match_author',len(byte_preservation)==len(input_exports)
          and all(r['bytes_identical'] and r['manifest_sha256']==r['author_export_sha256'] for r in byte_preservation),byte_preservation,section='integrity_only')
    write_json('no_kover_input_preservation.json',byte_preservation)

    # Bounded author replay: no main, no costs/source re-review, no disk inputs.
    ns = dict(__file__=str(OUT/'not_written_overlay.py'),__name__='mr10_pinned_overlay')
    exec(compile(blob(ORIGINAL,OP+'overlay.py'),ORIGINAL+':overlay.py','exec'),ns)
    params = js(ORIGINAL,OP+'inputs/tsiri_inputs.json')
    overrides = js(ORIGINAL,OP+'inputs/tsiri_overrides.json')
    def frozen_parameters(scenario):
        p = dict(params['scenarios'][scenario]); p.update(overrides.get('scenarios',{}).get(scenario,{}))
        return p,params['ufa_reference_basket_rub']
    ns['parameters'] = frozen_parameters
    correction_tree=ast.parse(blob(B,BP+'build.py'))
    candidate_function=next(n for n in correction_tree.body if isinstance(n,ast.FunctionDef) and n.name=='corrected_instant')
    candidate_ns=dict(EPOCH=epoch,timedelta=timedelta)
    exec(compile(ast.Module(body=[candidate_function],type_ignores=[]),B+':corrected_instant','exec'),candidate_ns)
    candidate_instant=candidate_ns['corrected_instant']
    fixture_offsets=['-1','0','1435','1440','1495','1885','2879','2880','10079','10080','10081']
    check('B_exact_correction_function_matches_oracle',all(
        candidate_instant(dict(fixture,departure_utc_minute=offset),'departure') ==
        instant(dict(fixture,departure_utc_minute=offset),'departure') for offset in fixture_offsets),
        dict(extracted_function='corrected_instant',source_commit=B,absolute_offsets=fixture_offsets,
             fixture_row_date=fixture['date'],independent_method='Decimal minutes converted to epoch seconds'))
    ns['instant'] = candidate_instant
    for line,r in enumerate(sales,2):
        r['_source_csv_line']=line; r['_journey_id']='tsiri-sales-line-'+str(line)
    replay = []
    for k,s in summaries.items():
        network,scenario,policy_id = k
        take = lambda r:r['profile']==definition['profile'] and r['network']==network
        ll=[r for r in flights if take(r)]
        ss=[r for r in sales if take(r) and r['scenario']==scenario]
        cc={r['flight_id']:r for r in caps if take(r) and r['scenario']==scenario}
        bb=next(r for r in baseline if take(r) and r['scenario']==scenario)
        policy=next(p for p in definition['scenarios'] if p['id']==policy_id)
        result,_,_,_=ns['apply'](ll,ss,cc,bb,policy,definition)
        arithmetic_fields=[f for f,v in result.items() if isinstance(v,(int,float)) and not isinstance(v,bool)]
        old_ok=all(equal(result[f],old_summaries[k][f]) for f in arithmetic_fields)
        new_ok=all(equal(result[f],s['hypothetical_'+f+'_if_recovered'] if k in held_keys and f in admitted_fields else s[f]) for f in arithmetic_fields)
        replay.append(dict(network=network,author_scenario=scenario,scenario_id=policy_id,
                           numeric_fields=len(arithmetic_fields),original_arithmetic_equal=old_ok,
                           corrected_or_hypothetical_equal=new_ok,corrected_template_status=result['template_rotation_status']))
    check('B_40_original_day1_arithmetic_replay_before_gating',len(replay)==40 and all(r['original_arithmetic_equal'] and r['corrected_or_hypothetical_equal'] for r in replay),
          dict(rows=len(replay),scope='Supplied original arithmetic replay; no contract/tariff/source acceptance'),section='bounded_author_replay')
    write_csv('bounded_day1_replay.csv',replay)
    # Run author hits with the actual correction function, compare independent oracle.
    check('B_overlay_hits_matches_independent_fixture_oracle',all(
        ns['hits'](dict(fixture,departure_utc_minute=str(d),arrival_utc_minute=str(a)),day2)==expected
        for _,d,a,expected in fixtures),section='bounded_author_replay')
    # Exercise the actual horizon guard before any economics, including exact end.
    horizon_results=[]
    for name,arrival,expected_reject in [('before_horizon',10079,False),('at_horizon',10080,True),('after_horizon',10081,True)]:
        leg=dict(selected[0],network='H_UFA_8',origin='UFA',destination='XXX',
                 departure_utc_minute=str(arrival-1440-60),arrival_utc_minute=str(arrival-1440),block_minutes='60')
        lastday=dict(definition,episode=dict(definition['episode'],start_utc='2026-12-12T00:00:00+00:00',end_utc_exclusive='2026-12-13T00:00:00+00:00'))
        bb=dict(scenario='base',network='H_UFA_8',contribution_before_base_fleet_opportunity='0')
        policy=next(p for p in definition['scenarios'] if p['action']=='delay')
        try:
            ns['apply']([leg],[],{leg['id']:{'capacity_scenario':'100','occupied':'0'}},bb,policy,lastday)
            rejected=False; message=''
        except ValueError as e:
            rejected=True; message=str(e)
        horizon_results.append(dict(name=name,arrival_if_delayed=instant(leg,'arrival',1440).isoformat(),
                                    expected_rejection=expected_reject,actual_rejection=rejected,error=message))
    check('B_horizon_guard_before_at_after',all(r['expected_rejection']==r['actual_rejection']
          and (not r['actual_rejection'] or r['error']=='delay outside tested weekly horizon; separate accrual accounting required') for r in horizon_results),horizon_results,section='bounded_author_replay')
    negative=dict(day2,start_utc=day2['end_utc_exclusive'],end_utc_exclusive=day2['start_utc'])
    try:
        ns['hits'](example,negative); rejected=False
    except ValueError:
        rejected=True
    check('B_negative_interval_rejected',rejected,section='bounded_author_replay')
    write_json('counterexamples.json',dict(
        source_id_only_join='Same SVX source_id/URL has different Nov8 and Nov9 raw hashes; inspect lineage_receipts.json.',
        absolute_minutes=dict(flight_id=example['id'],row_date=example['date'],minute=1885,
                              expected_utc=instant(example,'departure').isoformat(),original_wrong_utc=old_instant(example,'departure').isoformat()),
        day2=dict(original_affected=len(old_hits),corrected_affected=len(new_hits)),
        half_open=fixture_results,horizon=horizon_results,
        modulo_loses_rollover=dict(departure_1435=instant(arrival_fixture,'departure').isoformat(),arrival_1495=instant(arrival_fixture,'arrival').isoformat()),
        conflict_scope='Fixed planning labels with adjacent 45-minute continuity; alternative assignments, real tails and recovery UNKNOWN',
        admission_scope='Summary/journey served/unserved/money NULL for 4 held cases; physical allocations and cash retained only with HOLD/hypothetical status'))
    for item in js(B,BP+'source_manifest.json')['inputs']:
        data=blob(item['commit'],item['path'])
        check('B_input_lock:'+item['path'],sha(data)==item['sha256'] and len(data)==item['bytes'],section='integrity_only')
    return dict(selected_legs=len(selected),events=len(projection),wrong_original_events=70,wrong_original_physical_rows=wrong_original,
                day2_old=len(old_hits),day2_corrected=len(new_hits),conflicts_per_scenario=conflicts_by_network,
                held_cases=[list(k) for k in sorted(held_keys)],tables=dict(summary=len(summary),physical=len(physical),journeys=len(journeys),cash=len(cash)))


def main():
    blob(PREP,P+'contract.md'); blob(PREP,P+'briefs/correction_review.md')
    js(SJR,P+'source_join_review/findings.json'); js(CKR,P+'cost_kover_review/findings.json')
    verify_manifest(A,AP); verify_manifest(B,BP)
    a=review_a(); b=review_b()
    write_json('source_manifest.json',dict(review_id='MR10',read_policy='git show exact SHA only; no live input folders',
        prepared_root=PREP,corrections=dict(A=A,B=B),inputs=list(SOURCES.values()),
        authorship='Independent reviewer implementation; author overlay replay labelled separately',
        raw_content_review='NOT_RUN; neither raw acquisition nor cost/source review repeated'))
    result=dict(review_id='MR10',A=a,B=b,checks=CHECKS,
                totals=dict(collections.Counter(r['status'] for r in CHECKS)))
    write_json('checks.json',result)
    print(json.dumps(dict(A=a,B=b,totals=result['totals'],failures=[r for r in CHECKS if r['status']=='FAIL']),ensure_ascii=False,indent=2))
    if any(r['status']=='FAIL' for r in CHECKS):
        raise SystemExit(1)


if __name__=='__main__':
    main()
