#!/usr/bin/env python3
"""Coordinator intake, not independent acceptance or a full solver replay."""
import csv
import hashlib
import io
import json
import math
import subprocess
from pathlib import Path

NETWORK = '941d9ebfe97c86baa210da2c56bb1f94cbe298b0'
METHODS = '48686bf2276c435d7a260f4de6741c9b65d26e32'
N = 'context/28_evening_run_20261110/network/'
M = 'context/28_evening_run_20261110/methods/'

def blob(sha, path):
    return subprocess.check_output(['git', 'show', sha + ':' + path])

def rows(sha, path):
    return list(csv.DictReader(io.StringIO(blob(sha, path).decode())))

def near(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-6), (a, b)

checks = {}
manifest = json.loads(blob(NETWORK, N + 'input_manifest.json'))
for r in manifest:
    source, copied = blob(r['commit'], r['path']), blob(NETWORK, N + r['local'])
    assert source == copied
    assert len(copied) == r['bytes']
    assert hashlib.sha256(copied).hexdigest() == r['sha256']
checks['network_exact_source_and_copy_hashes'] = len(manifest)

inputs = rows(NETWORK, N + 'outputs/demand_fare_inputs.csv')
lookup = {(r['scenario'], r['origin'], r['destination']): r for r in inputs}
params = rows(NETWORK, N + 'inputs/owner4a976/data/assumptions/network.csv')
P = {s: {r['parameter']: float(r[s]) for r in params} for s in ('base', 'cautious')}

def pool(s, a, b):
    r = lookup[(s, a, b)]
    near(float(r['annual_od_model_both_directions']) / 104, r['diagnostic_week_od_one_direction'])
    return float(r['captured_local_one_direction']), float(r['net_fare_rub'])

def independent_two_leg_optimum(cap, d1, d2, dt, u1, u2, ut):
    # Conditional on through journeys z, local optima are independent.
    # The piecewise-linear maximum is at an endpoint or a local-capacity kink.
    top = min(cap, dt)
    choices = {0.0, top}
    choices.update(z for z in (cap-d1, cap-d2) if 0 <= z <= top)
    options = []
    for z in choices:
        x = min(d1, cap-z) if u1 > 0 else 0.0
        y = min(d2, cap-z) if u2 > 0 else 0.0
        options.append((x*u1+y*u2+z*ut, x, y, z))
    return max(options)

sync = rows(NETWORK, N + 'outputs/C01_synchronization.csv')
for r in sync:
    s = r['scenario']; p = P[s]['pax_cost_rub']; cap = float(r['capacity_per_leg_one_direction'])
    d1, f1 = pool(s, 'NJC', 'UFA'); d2, f2 = pool(s, 'UFA', 'MRV')
    t = lookup[(s, 'NJC', 'MRV')]
    dt = float(t['diagnostic_week_od_one_direction']) * min(P[s]['capture_transfer']*(1-math.exp(-2/3)), float(t['capture_scenario']))
    ft = float(t['net_fare_rub']) * P[s]['transfer_fare_factor']
    loss = float(r['local_loss_fraction_south'])
    value, x, y, z = independent_two_leg_optimum(cap, d1, d2*(1-loss), dt, f1-p, f2-p, ft-2*p)
    delta = 2*(value-d1*(f1-p)-d2*(f2-p))
    near(delta, r['delta_contribution_rub_week'])
    near(2*(x+y+z), r['total_journeys_week'])
    near(2*(x+y+2*z), r['segments_week'])
    near(float(r['contribution_sync_rub_week'])-float(r['contribution_unsync_rub_week']), delta)
checks['C01_piecewise_allocation_and_delta_rows'] = len(sync)

chain = rows(NETWORK, N + 'outputs/C07_extension.csv')
for r in chain:
    s = r['scenario']; A=P[s]; p=A['pax_cost_rub']; cap=2*A['seats']*A['lf_max']
    q1, f1=pool(s,'SVX','OMS'); q2, f2=pool(s,'OMS','KJA'); t=lookup[(s,'SVX','KJA')]
    dt=float(t['diagnostic_week_od_one_direction'])*min(A['capture_transfer']*(1-math.exp(-2/3)),float(t['capture_scenario']))
    ft=float(t['net_fare_rub'])*A['transfer_fare_factor']
    value,x,y,z=independent_two_leg_optimum(cap,q1,q2,dt,f1-p,f2-p,ft-2*p)
    bh=135/60
    added_fixed=4*((A['fuel_t_per_hour']*bh+A['fuel_t_per_cycle'])*A['fuel_rub_per_t']+(A['mro_rub_per_hour']+A['crew_rub_per_hour']+A['navigation_rub_per_hour'])*bh+A['ground_rub_per_flight']+A['deicing_rub_per_flight'])
    near(added_fixed,r['extra_fixed_flight_cost_rub_week'])
    near(2*(value-q1*(f1-p))-added_fixed,r['delta_contribution_rub_week'])
    turn=float(r['turn_minutes']); delay=270+3*turn-50
    near(delay,r['return_delay_vs_published_minutes'])
    from datetime import datetime, timedelta
    expected=datetime(2026,12,9,1,35)+timedelta(minutes=delay+turn)
    assert expected.isoformat()==r['next_SVX_departure_earliest_local']
checks['C07_delta_cost_and_timing_rows'] = len(chain)

programs=rows(NETWORK,N+'outputs/fixed_programs.csv')
routes=rows(NETWORK,N+'outputs/fixed_routes.csv')
for r in programs:
    selected=[x for x in routes if (x['network'],x['scenario'])==(r['network'],r['scenario'])]
    assert len(selected)==int(r['routes'])
    for summary,detail in [('block_hours_week','block_hours_week'),('contribution_rub_week','local_only_contribution_rub_week')]:
        near(r[summary],sum(float(x[detail]) for x in selected))
checks['fixed_program_route_aggregation_rows']=len(programs)

sources=json.loads(blob(METHODS,M+'source_manifest.json'))['files']
for r in sources:
    copied=blob(METHODS,M+r['path'])
    assert hashlib.sha256(copied).hexdigest()==r['sha256']
    assert copied==blob(r['source_commit'],r['source_path'])
checks['methods_source_hashes']=len(sources)
outs=json.loads(blob(METHODS,M+'output_manifest.json'))['files']
for r in outs:
    b=blob(METHODS,M+r['path'])
    assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
checks['methods_output_hashes']=len(outs)
candidates=rows(METHODS,M+'runs/selection_v1/all_candidates.csv')
frontier=rows(METHODS,M+'runs/selection_v1/preserved_frontiers.csv')
assert len(candidates)==384 and len(frontier)==303
assert len({r['id'] for r in candidates})==384
by_id={r['id']:r for r in candidates}
for r in frontier:
    source=by_id[r['selected_id']]
    near(source['contribution_rub_year'],r['contribution_rub_year'])
    assert int(source['cap'])<=int(r['cap'])
old=by_id['AUTHOR_52_48_CONCENTRATED/base/OMS/GREEDY/cap10']
better=by_id['AUTHOR_52_48_CONCENTRATED/base/OMS/GREEDY/cap4']
assert float(better['contribution_rub_year'])>float(old['contribution_rub_year'])
checks['methods_frontier_source_rows']=len(frontier)
checks['OMS_found_set_gain_rub_year']=float(better['contribution_rub_year'])-float(old['contribution_rub_year'])
result={'network_sha':NETWORK,'methods_sha':METHODS,'status':'COORDINATOR_INTAKE_PASS_INDEPENDENT_REVIEW_PENDING','checks':checks,'limits':['No full methods solver replay','No market or fleet availability acceptance','Diagnostic week is not annual profit','C01 hypothetical same flights is not a confirmed RW retiming opportunity','C07 own transfer baseline remains unknown','Four Sol slots occupied; independent review queued']}
dest=Path(__file__).with_name('early_packages_checks.json')
dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
