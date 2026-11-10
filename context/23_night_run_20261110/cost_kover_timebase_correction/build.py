#!/usr/bin/env python3
"""Pinned MR02 timebase correction; inherited arithmetic is not independently accepted."""
import collections
import csv
import hashlib
import io
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
PIN = 'afadee35ebeefe54a05bdfc5b3e224a370f90e0a'
PREFIX = 'context/23_night_run_20261110/cost_kover/'
LOCK = []


def digest(b):
    return hashlib.sha256(b).hexdigest()


def blob(path):
    b = subprocess.check_output(['git', 'show', PIN + ':' + PREFIX + path])
    LOCK.append(dict(commit=PIN, path=PREFIX + path, sha256=digest(b), bytes=len(b)))
    return b


def rows(path):
    return list(csv.DictReader(io.StringIO(blob(path).decode('utf-8-sig'))))


def js(name, x):
    (ROOT / name).write_text(json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def csvout(name, rr):
    fields = list(dict.fromkeys(k for r in rr for k in r))
    with (ROOT / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rr)


definition = json.loads(blob('scenario_definitions.json'))
params = json.loads(blob('inputs/tsiri_inputs.json'))
overrides = json.loads(blob('inputs/tsiri_overrides.json'))
flights = rows('inputs/tsiri_flights.csv')
sales = rows('inputs/tsiri_sales.csv')
caps = rows('inputs/tsiri_capacity.csv')
baseline = rows('inputs/tsiri_comparison.csv')
original_summary = rows('scenario_summary.csv')
code = blob('overlay.py').decode()
ns = dict(__file__=str(ROOT / 'pinned_overlay_not_written.py'), __name__='pinned_overlay')
exec(compile(code, PIN + ':overlay.py', 'exec'), ns)
old_instant = ns['instant']
EPOCH = datetime.fromisoformat(definition['period_start']).replace(tzinfo=timezone.utc)
assert definition['period_start'] == '2026-12-07'


def corrected_instant(leg, event):
    # UTC minutes in this exact author export are absolute offsets from model week.
    # Row date remains source metadata; adding it again would count days twice.
    return EPOCH + timedelta(minutes=float(leg[event + '_utc_minute']))


def frozen_parameters(scenario):
    p = dict(params['scenarios'][scenario])
    p.update(overrides.get('scenarios', {}).get(scenario, {}))
    return p, params['ufa_reference_basket_rub']


ns['parameters'] = frozen_parameters  # same pinned JSON values, read from memory
selected = [r for r in flights if r['profile'] == definition['profile'] and r['network'] in definition['networks']]
times = []
for r in selected:
    for event in ['departure', 'arrival']:
        a, b = old_instant(r, event), corrected_instant(r, event)
        times.append(dict(profile=r['profile'], network=r['network'], flight_id=r['id'],
                          source_date=r['date'], event=event, absolute_minute=r[event + '_utc_minute'],
                          old_utc=a.isoformat(), corrected_utc=b.isoformat(),
                          old_minus_corrected_minutes=(a - b).total_seconds() / 60))
csvout('timestamp_projection.csv', times)

u8 = [r for r in selected if r['network'] == 'H_UFA_8']
episode2 = dict(definition['episode'], start_utc='2026-12-08T00:00:00+00:00', end_utc_exclusive='2026-12-09T00:00:00+00:00')
ns['instant'] = old_instant
old_touched = [r['id'] for r in u8 if ns['hits'](r, episode2)]
ns['instant'] = corrected_instant
new_touched = [r['id'] for r in u8 if ns['hits'](r, episode2)]
assert len(old_touched) == 0 and len(new_touched) == 16
assert all(corrected_instant(r, 'departure') == EPOCH + timedelta(minutes=float(r['departure_utc_minute'])) for r in selected)

# Half-open boundaries are tested on explicit absolute-minute fixtures.
fixture = dict(u8[0], origin='UFA', destination='XXX', departure_utc_minute=1440, arrival_utc_minute=1500)
assert ns['hits'](fixture, episode2)
fixture['departure_utc_minute'] = 2880
assert not ns['hits'](fixture, episode2)
assert not ns['hits'](dict(u8[0], origin='XXX', destination='XXX'), episode2)

for line, r in enumerate(sales, 2):
    r['_source_csv_line'] = line
    r['_journey_id'] = 'tsiri-sales-line-' + str(line)
old_by = {(r['network'], r['author_scenario'], r['scenario_id']): r for r in original_summary}
summaries, physical, journeys, cash, issues = [], [], [], [], []
money_equal = 0
for network in definition['networks']:
    for scenario in definition['author_scenarios']:
        take = lambda r: r['profile'] == definition['profile'] and r['network'] == network
        ll = [r for r in flights if take(r)]
        ss = [r for r in sales if take(r) and r['scenario'] == scenario]
        cc = {r['flight_id']: r for r in caps if take(r) and r['scenario'] == scenario}
        bb = next(r for r in baseline if take(r) and r['scenario'] == scenario)
        for policy in definition['scenarios']:
            result, ls, jj, ee = ns['apply'](ll, ss, cc, bb, policy, definition)
            old = old_by[network, scenario, policy['id']]
            for field in ['author_contribution_rub', 'overlay_delta_before_unknown_rub',
                          'contribution_after_overlay_before_unknown_rub', 'lost_net_revenue_rub']:
                assert math.isclose(result[field], float(old[field]), abs_tol=1e-6, rel_tol=1e-12)
            money_equal += 1
            unresolved = result['template_rotation_status'] != 'TEMPLATE_ONLY_CONTINUITY_PASS'
            result['timebase_epoch_utc'] = EPOCH.isoformat()
            result['timebase_correction_source_commit'] = PIN
            result['acceptance_scope'] = 'PARENT_TIMEBASE_AND_DELTA_CHECK_ONLY; INHERITED_ARITHMETIC_REVIEW_PENDING'
            result['usable_as_served_schedule'] = False  # even PASS is only planning-label continuity
            if policy['action'] == 'delay':
                touched = {r['id'] for r in ll if ns['hits'](r, definition['episode'])}
                shifted = [dict(r, departure_utc_minute=float(r['departure_utc_minute']) + (1440 if r['id'] in touched else 0),
                                arrival_utc_minute=float(r['arrival_utc_minute']) + (1440 if r['id'] in touched else 0)) for r in ll]
                found = ns['template_rotation'](shifted, reference=ll)
                issues.extend(dict(network=network, scenario=scenario, **x) for x in found)
                result['rotation_conflicts'] = len(found)
                if network == 'H_UFA_8':
                    assert len(found) == 23
                if unresolved:
                    # Preserve the arithmetic as an explicitly unachieved completion fixture.
                    for field in ['remaining_endpoint_journeys', 'unserved_endpoint_journeys', 'unserved_segment_allocations', 'overlay_delta_before_unknown_rub',
                                  'contribution_after_overlay_before_unknown_rub', 'additional_cash_peak_timing_stress_rub']:
                        result['hypothetical_' + field + '_if_recovered'] = result[field]
                        result[field] = None
                    result['value_status'] = 'HOLD_DELAY_COMPLETION_UNRESOLVED_ROTATION'
                    for row in jj:
                        for field in ['conditionally_served_endpoint_journeys', 'unserved_endpoint_journeys', 'retained_net_fare_rub']:
                            row['hypothetical_' + field + '_if_recovered'] = row[field]
                            row[field] = None
                        row['value_status'] = 'HOLD_DELAY_COMPLETION_UNRESOLVED_ROTATION'
                    for row in ee:
                        row['value_status'] = 'HYPOTHETICAL_COMPLETION_CASH_NOT_AVAILABLE_SCHEDULE'
                    for row in ls:
                        row['value_status'] = 'HOLD_DELAY_COMPLETION_UNRESOLVED_ROTATION'
            for row in [result] + ls + jj + ee:
                row['parent_input_set_id'] = row['input_set_id']
                row['input_set_id'] = 'MR02-TIMEBASE-CORRECTION:afadee35'
                row['run_id'] = 'MR02-timebase-correction-v1'
                row['source_overlay_commit'] = PIN
                row['acceptance_scope'] = 'PARENT_TIMEBASE_AND_DELTA_CHECK_ONLY; INHERITED_ARITHMETIC_REVIEW_PENDING'
            summaries.append(result)
            physical.extend(ls)
            journeys.extend(jj)
            cash.extend(ee)

csvout('scenario_summary.csv', summaries)
csvout('physical_leg_status.csv', physical)
csvout('affected_journeys.csv', journeys)
csvout('cash_fixture.csv', cash)
csvout('rotation_conflicts.csv', issues)
js('checks.json', dict(status='PASS_PARENT_SCOPED_CORRECTION_CHECKS',
    source_commit=PIN, period_start=definition['period_start'], selected_flight_rows=len(selected),
    timestamp_fields_checked=len(times), changed_timestamp_fields=sum(r['old_minus_corrected_minutes'] != 0 for r in times),
    day2_u8_original_touched=len(old_touched), day2_u8_corrected_touched=len(new_touched),
    day2_corrected_flight_ids=new_touched, day1_scenario_arithmetic_unchanged_rows=money_equal,
    u8_delay_rotation_conflicts_each_scenario=23, half_open_boundary_checks='PASS',
    gated_delay_summaries=sum(r['value_status'].startswith('HOLD') for r in summaries),
    preserved_no_kover_source='Original git export bytes unchanged; derived timestamps corrected separately',
    actual_recovery_fleet='UNKNOWN; NOT_INVENTED', market_launch='NOT_ACCEPTED', independent_review='NOT_RUN_ON_CORRECTION'))
js('source_manifest.json', dict(inputs=LOCK, input_policy='Exact Git blobs read-only; no network or live owner folders'))
files = []
for p in sorted(ROOT.iterdir()):
    if p.is_file() and p.name not in {'output_manifest.json', 'handoff.json'}:
        b = p.read_bytes()
        files.append(dict(path=p.name, sha256=digest(b), bytes=len(b)))
js('output_manifest.json', dict(package_id='MR02-timebase-correction-v1', files=files,
    acceptance='PARENT_TIMEBASE_AND_DELTA_CHECK_ONLY'))
js('handoff.json', dict(package_id='MR02-timebase-correction-v1', original_commit=PIN,
    status='PARENT_SCOPED_CORRECTION; INDEPENDENT_RECHECK_NOT_RUN',
    source_epoch='scenario_definitions.period_start UTC + absolute author minutes',
    manifest_sha256=digest((ROOT / 'output_manifest.json').read_bytes()),
    read_first='README.md', prior_verdict_scope='Original MR02 independent review remains on afadee',
    no_new_recovery='Conflicting delayed programme held; all-served quantities and resulting money NULL, conditional algebra retained separately'))
print(json.dumps(json.loads((ROOT / 'checks.json').read_text()), ensure_ascii=False))
