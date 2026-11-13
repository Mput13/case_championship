#!/usr/bin/env python3
"""Canonical turn60/90 delay supplement. No financial calculations or changes.

The original delay_summary/details are retained as historical turn60 outputs.
Each stress is compared with its OWN zero-shock, padded baseline. A turn90
baseline that fails the published timetable remains explicitly infeasible.
"""
import sys
sys.dont_write_bytecode = True
import csv
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import core as C

HERE = Path(__file__).resolve().parent
FILES = ['delay_stress_summary.csv', 'delay_stress_cases.csv',
         'delay_stress_baselines.csv', 'delay_stress_trajectories.csv']


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(name, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (HERE / name).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: 'NULL' if v is None else json.dumps(v, ensure_ascii=False, separators=(',', ':'))
                             if isinstance(v, (list, dict)) else v for k, v in row.items()})


def replay(seq, turn, initial_position, shock=None, hold=0, baseline_target=None):
    ready = None  # Explicitly conditional readiness before padded context.
    position = initial_position
    out = []
    for flight in seq:
        planned = C.M.dt(flight['departure_utc'])
        arrival = C.M.dt(flight['arrival_utc'])
        actual = max(planned, ready) if ready is not None else planned
        if flight['flight_id'] == shock:
            assert baseline_target is not None
            actual = max(actual, baseline_target + timedelta(minutes=hold))
        landed = actual + (arrival - planned)
        out.append(dict(departure=actual, arrival=landed,
                        delay=(actual - planned).total_seconds() / 60,
                        position_fail=position != flight['origin']))
        ready = landed + timedelta(minutes=turn)
        position = flight['destination']
    return out


def checks_synthetic():
    def f(i, dep, arr):
        base = datetime(2027, 1, 31, 21, tzinfo=C.UTC)
        return dict(flight_id=i, origin='SVX' if i != 'b' else 'KJA',
                    destination='KJA' if i != 'b' else 'SVX',
                    departure_utc=(base + timedelta(minutes=dep)).isoformat(),
                    arrival_utc=(base + timedelta(minutes=arr)).isoformat())
    seq = [f('a', 0, 120), f('b', 180, 300), f('c', 600, 720)]
    b60 = replay(seq, 60, 'SVX')
    b90 = replay(seq, 90, 'SVX')
    assert [x['delay'] for x in b60] == [0, 0, 0]
    assert [x['delay'] for x in b90] == [0, 30, 0]
    for turn, baseline in [(60, b60), (90, b90)]:
        for hold in [30, 60, 120]:
            shock = replay(seq, turn, 'SVX', 'a', hold, baseline[0]['departure'])
            assert shock[0]['delay'] == hold
            assert shock[1]['delay'] == hold + turn - 60
            assert shock[2]['delay'] == 0
            assert shock[1]['departure'].month == 2  # No midnight/month reset.
        shock = replay(seq, turn, 'SVX', 'b', 30, baseline[1]['departure'])
        assert (shock[1]['departure'] - baseline[1]['departure']).total_seconds() == 1800
    return 'PASS: baseline90 failure, incremental-vs-total, holds, month seam, absorption'


def build():
    locked = {p.name: sha(p) for p in HERE.iterdir() if p.is_file()
              and p.suffix in ('.csv', '.json', '.svg') and not p.name.startswith('delay_stress_')}
    finals = C.js(HERE / 'search_coverage.json')['same_K2_distinct_finalists']
    cases, baselines, summaries, trajectories = [], [], [], []
    groups = {}
    for cid in finals:
        template = C.templates()[cid]
        annual = C.annual_calendar({m: template['states']['REPLACE'] for m in range(1, 13)}, template['tails'])
        assert annual['status'] == 'PERIODIC_YEAR_STITCH_PASS_CONDITIONAL'
        for tail in template['tails']:
            seq = sorted((f for f in annual['events'] if f['tail'] == tail['id']), key=lambda f: f['departure_utc'])
            if not seq:
                assert tail.get('reserve'), tail
                continue
            for turn in [60, 90]:
                baseline = replay(seq, turn, tail['initial_location'])
                year_ids = [i for i, f in enumerate(seq) if C.M.dt(f['departure_utc']).year == 2027]
                bad = [i for i in year_ids if baseline[i]['delay'] > 1e-8 or baseline[i]['position_fail']]
                baseline_ok = not bad
                baselines.append(dict(candidate=cid, tail=tail['id'], turn_minutes=turn,
                    zero_shock=True, planned_schedule_feasible_2027=baseline_ok,
                    delayed_baseline_flights_2027=len(bad),
                    maximum_baseline_delay_minutes=max(baseline[i]['delay'] for i in year_ids),
                    first_baseline_failure=seq[bad[0]]['flight_id'] if bad else None,
                    first_context_departure=seq[0]['departure_utc'],
                    last_context_arrival=seq[-1]['arrival_utc'],
                    readiness_before_context='CONDITIONAL_UNKNOWN; periodic padding, not actual roster',
                    baseline_interpretation='EARLIEST_READY_NOT_APPROVED_RETIMING' if bad else 'CONDITIONAL_PLANNED_TIME_REPLAY',
                    crew_slots_MRO='UNKNOWN'))
                assert not any(x['position_fail'] for x in baseline)
                if turn == 60:
                    assert baseline_ok
                for season, month in [('winter', 2), ('spring', 4), ('summer', 7), ('autumn', 10)]:
                    start = datetime(2027, month, 8, tzinfo=C.UTC)
                    start -= timedelta(days=start.weekday())
                    end = start + timedelta(days=7)
                    month_end = C.M.bounds(2027, month)[1]
                    for idx, target in enumerate(seq):
                        trigger_dep = C.M.dt(target['departure_utc'])
                        in_scope = start <= trigger_dep < end or month_end - timedelta(days=2) <= trigger_dep < month_end or (
                            season == 'winter' and datetime(2027, 12, 30, tzinfo=C.UTC) <= trigger_dep < datetime(2028, 1, 1, tzinfo=C.UTC))
                        if not in_scope:
                            continue
                        kind = 'new' if target['rotation_id'].startswith('NEW-') else 'retained'
                        indices = [i for i in range(idx, len(seq))
                                   if C.M.dt(seq[i]['departure_utc']) <= trigger_dep + timedelta(days=14)]
                        for hold in [30, 60, 120]:
                            shock = replay(seq, turn, tail['initial_location'], target['flight_id'], hold, baseline[idx]['departure'])
                            delta = {i: (shock[i]['departure'] - baseline[i]['departure']).total_seconds() / 60 for i in indices}
                            assert abs(delta[idx] - hold) < 1e-8
                            assert all(v >= -1e-8 for v in delta.values())
                            affected = [i for i in indices if i > idx and delta[i] > 1e-8]
                            old = sorted({seq[i]['rotation_id'].split('@')[0] for i in affected
                                          if not seq[i]['rotation_id'].startswith('NEW-')})
                            absorbed = next((i for i in indices if i > idx and delta[i] <= 1e-8), None)
                            row = dict(candidate=cid, season=season, turn_minutes=turn, hold_minutes=hold,
                                target_kind=kind, trigger=target['flight_id'], tail=tail['id'],
                                trigger_planned_utc=target['departure_utc'],
                                baseline_trigger_utc=baseline[idx]['departure'].isoformat(),
                                shocked_trigger_utc=shock[idx]['departure'].isoformat(),
                                planned_schedule_feasible=baseline_ok,
                                baseline_status='PASS_CONDITIONAL' if baseline_ok else 'FAIL_AS_PUBLISHED; NO_APPROVED_RESCHEDULE',
                                max_baseline_departure_delay=max(baseline[i]['delay'] for i in indices),
                                max_total_departure_delay=max(shock[i]['delay'] for i in indices),
                                max_incremental_departure_delay=max(delta.values()),
                                incremental_downstream_flights=len(affected), affected_old_ids_incremental=old,
                                extra_buffer_needed_minutes=max([delta[i] for i in affected] or [0]),
                                first_absorbed_at=seq[absorbed]['flight_id'] if absorbed is not None else None,
                                crosses_month=any(C.M.dt(seq[i]['departure_utc']).month != trigger_dep.month or
                                                  shock[i]['departure'].month != C.M.dt(seq[i]['departure_utc']).month for i in affected),
                                crosses_week=any(C.M.dt(seq[i]['departure_utc']).isocalendar()[:2] != trigger_dep.isocalendar()[:2] for i in affected),
                                crosses_year=any(shock[i]['departure'].year != trigger_dep.year for i in affected),
                                hold_definition='extra hold relative to same-turn zero-shock earliest-ready baseline',
                                cancellation_or_swap_cutoff=None, monetary_effect=None, actual_crew_slot_limits=None)
                            cases.append(row)
                            key = cid, season, turn, hold, kind
                            groups.setdefault(key, []).append((row, seq, baseline, shock, delta, indices))
    for key, obs in sorted(groups.items()):
        cid, season, turn, hold, kind = key
        summaries.append(dict(candidate=cid, season=season, turn_minutes=turn, hold_minutes=hold, target_kind=kind,
            triggers=len(obs), planned_schedule_feasible=all(o[0]['planned_schedule_feasible'] for o in obs),
            baseline_failure_not_repaired=True,
            maximum_total_delay_minutes=max(o[0]['max_total_departure_delay'] for o in obs),
            maximum_incremental_delay_minutes=max(o[0]['max_incremental_departure_delay'] for o in obs),
            max_downstream_flights=max(o[0]['incremental_downstream_flights'] for o in obs),
            max_extra_buffer_minutes=max(o[0]['extra_buffer_needed_minutes'] for o in obs),
            affected_old_ids_incremental=sorted({x for o in obs for x in o[0]['affected_old_ids_incremental']}),
            unabsorbed_in_14_days=sum(o[0]['first_absorbed_at'] is None for o in obs),
            month_crossings=sum(o[0]['crosses_month'] for o in obs), year_crossings=sum(o[0]['crosses_year'] for o in obs),
            actual_recovery_approval=None, monetary_effect=None))
        # One independently inspectable trajectory for every group. All cases
        # retain full aggregate coverage; this avoids exporting redundant months.
        row, seq, base, shock, delta, indices = max(obs, key=lambda o: (
            o[0]['incremental_downstream_flights'], o[0]['max_total_departure_delay'], o[0]['trigger']))
        for i in indices:
            trajectories.append(dict(candidate=cid, season=season, turn_minutes=turn, hold_minutes=hold,
                target_kind=kind, trigger=row['trigger'], flight=seq[i]['flight_id'], tail=row['tail'],
                origin=seq[i]['origin'], destination=seq[i]['destination'],
                planned_departure_utc=seq[i]['departure_utc'], planned_arrival_utc=seq[i]['arrival_utc'],
                baseline_departure_utc=base[i]['departure'].isoformat(), baseline_arrival_utc=base[i]['arrival'].isoformat(),
                shocked_departure_utc=shock[i]['departure'].isoformat(), shocked_arrival_utc=shock[i]['arrival'].isoformat(),
                baseline_delay_minutes=base[i]['delay'], total_delay_minutes=shock[i]['delay'], incremental_minutes=delta[i],
                planned_schedule_feasible=row['planned_schedule_feasible']))
    assert len(summaries) == 3 * 4 * 2 * 3 * 2
    assert {r['turn_minutes'] for r in cases} == {60, 90}
    for cid in finals:
        assert any(r['candidate'] == cid and r['turn_minutes'] == 90 and not r['planned_schedule_feasible_2027'] for r in baselines)
    write(FILES[0], summaries)
    write(FILES[1], cases)
    write(FILES[2], baselines)
    write(FILES[3], trajectories)
    assert all(sha(HERE / n) == h for n, h in locked.items()), 'Existing financial/historical artifacts changed'
    receipt = dict(status='PASS_SCOPED_TURN60_90_CORRECTION', financial_recalculation=False,
        source_review='review/findings.csv P2 economics/calculate.py:608; historical turn60 outputs retained',
        synthetic=checks_synthetic(), summary_groups=len(summaries), cases=len(cases), trajectories=len(trajectories),
        baseline_rows=len(baselines), all_three_turn90_baselines_fail=True,
        actual_dispatch_approval=None, monetary_effect=None,
        initial_context='Padded periodic late2026 through January2028; actual initial readiness UNKNOWN',
        financial_artifacts_unchanged=locked,
        script_sha256=sha(Path(__file__)), output_sha256={name: sha(HERE / name) for name in FILES}, guard=C.guard())
    (HERE / 'delay_stress_validation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: receipt[k] for k in ['status', 'summary_groups', 'cases', 'trajectories', 'baseline_rows']}, ensure_ascii=False))


def verify():
    r = C.js(HERE / 'delay_stress_validation.json')
    assert r['script_sha256'] == sha(Path(__file__))
    assert all(sha(HERE / name) == h for name, h in r['output_sha256'].items())
    assert all(sha(HERE / name) == h for name, h in r['financial_artifacts_unchanged'].items())
    assert r['guard'] == C.guard()
    checks_synthetic()
    with (HERE / FILES[1]).open() as handle:
        cases = list(csv.DictReader(handle))
    assert {x['turn_minutes'] for x in cases} == {'60', '90'}
    assert all(x['baseline_status'].startswith('FAIL_AS_PUBLISHED') for x in cases if x['turn_minutes'] == '90')
    assert r['summary_groups'] == 144 and r['actual_dispatch_approval'] is None
    print('PASS: canonical turn60/90 receipts, baseline failures, immutable finance, synthetic recurrence')


if __name__ == '__main__':
    verify() if '--verify' in sys.argv else build()
