#!/usr/bin/env python3
"""Independent reconciliation of frozen stage17 exports; no colleague code execution."""
import collections
import csv
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess

BASE = Path(__file__).resolve().parents[1]
SHA = 'd437041c01724b711a172910c10e27b723d77a9c'
ROOT = 'context/17_aircraft_route_review'

def blob(path):
    b = subprocess.check_output(['git', 'show', SHA + ':' + path])
    p = BASE / 'raw' / 'aircraft_route_review' / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b)
    return b

def table(name):
    return list(csv.DictReader(io.StringIO(blob(ROOT + '/model/' + name).decode('utf-8-sig'))))

def num(r, k):
    assert k in r and r[k] != '', (k, r)
    v = float(r[k]); assert math.isfinite(v)
    return v

def close(a, b): return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-4)
def group(r): return r['profile'], r['network'], r['scenario']

def main():
    totals, sales, caps, flights = [table(n) for n in ['comparison.csv', 'sales.csv', 'capacity.csv', 'flights.csv']]
    byid = {(r['profile'], r['network'], r['id']): r for r in flights}
    assert len(byid) == len(flights)
    reports = []
    sums = ['sold_journeys', 'transfer_journeys', 'segment_pax', 'gross_revenue', 'foregone_RW_revenue', 'incremental_revenue', 'new_pax_variable', 'saved_old_pax_variable', 'migrated_RW_total']
    for t in totals:
        k = group(t); ss = [r for r in sales if group(r) == k]; cc = [r for r in caps if group(r) == k]
        checks = {'sum_' + f: close(num(t, f), sum(num(r, f) for r in ss)) for f in sums}
        checks['contribution'] = close(num(t, 'incremental_revenue') - num(t, 'incremental_operating_cost'), num(t, 'contribution_before_base_fleet_opportunity'))
        checks['cost_delta'] = close(num(t, 'flight_variable_cost') + num(t, 'new_pax_variable') - num(t, 'saved_old_pax_variable'), num(t, 'incremental_operating_cost'))
        checks['journey_segment_identity'] = close(num(t, 'sold_journeys') + num(t, 'transfer_journeys'), num(t, 'segment_pax'))
        used, od, demand = collections.Counter(), collections.Counter(), {}
        fare_ok = product_ok = True
        for r in ss:
            ids = r['flight_ids'].split(';'); q = num(r, 'sold_journeys'); transfer = r['transfer'] == 'True'
            legs = [byid[(k[0], k[1], i)] for i in ids]
            fare_ok &= close(q * num(r, 'fare_once'), num(r, 'gross_revenue'))
            product_ok &= len(ids) == (2 if transfer else 1)
            product_ok &= legs[0]['origin'] == r['origin'] and legs[-1]['destination'] == r['destination']
            if transfer:
                product_ok &= legs[0]['destination'] == legs[1]['origin']
                product_ok &= num(legs[1], 'departure_utc_minute') >= num(legs[0], 'arrival_utc_minute')
            for i in ids: used[i] += q
            od[(r['origin'], r['destination'])] += q
            demand[(r['origin'], r['destination'])] = num(r, 'D')
        checks['one_fare'] = bool(fare_ok); checks['dated_product_identity'] = bool(product_ok)
        checks['dated_capacity'] = all(close(used[r['flight_id']], num(r, 'occupied')) and used[r['flight_id']] <= num(r, 'capacity_scenario') + 1e-6 for r in cc)
        checks['scenario_seats'] = close(sum(num(r, 'capacity_scenario') for r in cc), num(t, 'scenario_segment_seats'))
        checks['od_bound'] = all(v <= demand[o] + 1e-6 for o, v in od.items())
        reports.append(dict(profile=k[0], network=k[1], scenario=k[2], checks=checks, all_arithmetic_checks_pass=all(checks.values())))
    # Preserve review inputs without running imports or builders.
    for p in ['README.md', 'assumptions.json', 'evidence/sources.json', 'evidence/variants.csv', 'evidence/directional_blocks.csv', 'evidence/published_service_facts.csv', 'model/route_variant_matrix.csv', 'model/previously_excluded_review.csv', 'model/validation.json']:
        blob(ROOT + '/' + p)
    blob('scripts/build_aircraft_route_review.py')
    errors = [r for r in reports if not r['all_arithmetic_checks_pass']]
    files = []
    for p in sorted((BASE / 'raw' / 'aircraft_route_review').rglob('*')):
        if p.is_file(): files.append(dict(path=str(p.relative_to(BASE)), sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bytes=p.stat().st_size))
    out = dict(generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(), input_sha=SHA, status='ARITHMETIC_PASS' if not errors else 'FAIL', results_checked=len(reports), sales_rows=len(sales), flight_rows=len(flights), capacity_rows=len(caps), errors=errors, results=reports, inputs=files, limitations='Independent exported-ledger identities only. No realised OD, fares, tail availability, dispatch/payload, contract, optimisation completeness or launch approval. Timetable is an offer, not performance.')
    (BASE / 'evidence' / 'stage17_checks.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: out[k] for k in ['input_sha', 'status', 'results_checked', 'sales_rows', 'flight_rows', 'capacity_rows', 'errors']}))

if __name__ == '__main__': main()
