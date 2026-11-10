"""Pinned, offline impact checks; writes only alongside this file. No model-wide/raw replay."""
import ast
import csv
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
BASE = '2f03b693a62c219e9475fcd1e26295039f6a49d7'
LATEST = 'b91e0672af396bacd91651abeff8732fa733859d'
CHECKOUT = 'd8ea350a0388d35f5b559f65a57109d862d2eb85'
P = Path(__file__).resolve().parent
ROOT = P.parents[2]

def write_json(name, value):
    (P / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def table(name, rows):
    with (P / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def source(sha, path):
    r = subprocess.run(['git', 'show', sha + ':' + path], capture_output=True, check=True)
    dest = P / 'inputs' / sha / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.stdout)
    return dest

def read(sha, path):
    return list(csv.DictReader(source(sha, path).open()))

extra = ['data/assumptions/longlist_params.csv', 'data/assumptions/weight_profiles.csv',
         'data/processed/demand_pairs.csv', 'data/processed/od_pairs.csv',
         'data/processed/catchment_extra.csv', 'data/manual/pax_2025_overrides.csv',
         'data/manual/airport_tech.csv', 'data/external/colleagues/README.md',
         'data/external/colleagues/stage1_audit/release_note.md',
         'data/external/colleagues/stage1_audit/main_source_checks.md',
         'src/fetch_weather.py', 'src/longlist_data.py', 'src/update.py',
         'src/transfer_potential.py', 'tests/test_stage1_weather.py']
for name in extra:
    source(LATEST, name)
for name in ('briefs/late_colleague_impact.md','contract.md','freeze_0930.json'):
    source(CHECKOUT, 'context/23_night_run_20261110/' + name)

comparisons = []
for sha in (BASE, LATEST):
    for name in ('longlist_scores.csv', 'longlist_scores_min500.csv', 'longlist_scores_min500_strict.csv'):
        p = P / 'inputs' / sha / 'data/processed' / name
        if not p.exists():
            continue
        for r in list(csv.DictReader(p.open()))[:3]:
            comparisons.append(dict(source_sha=sha, mode=name, **{k: r.get(k, '') for k in
                ('iata', 'rank', 'city', 'score', 'score_low', 'score_high', 'rank_best', 'rank_worst',
                 'unknown_weight_share', 'weak_weight_share', 'top3_share_random')}))
table('compared_top3.csv', comparisons)

old = {(r['scenario'], r['hub']): r for r in read(BASE, 'data/processed/network_summary.csv')}
new = read(LATEST, 'data/processed/network_summary.csv')
money = []
for r in new:
    before = old[(r['scenario'], r['hub'])]
    row = dict(scenario=r['scenario'], variant=r['variant'], old_source_sha=BASE, new_source_sha=LATEST,
               grain='scenario x alternative network; annual both directions; RUB million')
    for k in ('aircraft', 'segments_year', 'od_trips_year', 'transfer_od_year', 'revenue_mln_year',
              'var_cost_mln_year', 'result_mln_year', 'share_pp'):
        row.update({k + '_old': before[k], k + '_new': r[k], k + '_delta': round(float(r[k]) - float(before[k]), 6)})
    row['rounded_money_residual_mln'] = int(r['result_mln_year']) - (int(r['revenue_mln_year']) - int(r['var_cost_mln_year']))
    row['rounded_conservation_residual_pax'] = int(r['segments_year']) - int(r['od_trips_year']) - int(r['transfer_od_year'])
    assert abs(row['rounded_money_residual_mln']) <= 1
    assert abs(row['rounded_conservation_residual_pax']) <= 1
    money.append(row)
table('compared_economics.csv', money)

# Compile the author's exact functions, excluding module-level IO and unused imports.
netpath = P / 'inputs' / LATEST / 'src/network_model.py'
tree = ast.parse(netpath.read_text())
names = {'leg_cost', 'fare', 'capture', 'leg_share', 'freq_for', 'hub_network', 'direct_network'}
ns = dict(math=math, CLOSED=set())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[]), str(netpath), 'exec'), ns)
A = {r['parameter']: float(r['base']) for r in read(LATEST, 'data/assumptions/network.csv')}
ns['A'] = A
direct = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'direct_network')
joint = next(n for n in direct.body if isinstance(n, ast.FunctionDef) and n.name == 'joint')
exec(compile(ast.Module(body=[joint], type_ignores=[]), str(netpath), 'exec'), ns)

# Real exported repeated pair: author's observed segment input, frequencies, costs and capture.
routes = read(LATEST, 'data/processed/network_routes.csv')
demand = read(LATEST, 'data/processed/demand_pairs.csv')
pool_rows = []
for scenario in ('base', 'cautious'):
    AA = {r['parameter']: float(r[scenario]) for r in read(LATEST, 'data/assumptions/network.csv')}
    groups = {}
    for r in routes:
        if r['scenario'] == scenario and r['variant'].startswith('Прямые'):
            groups.setdefault(tuple(sorted((r['from'], r['to']))), []).append(r)
    for pair, rs in groups.items():
        if len(rs) < 2:
            continue
        dr = next((r for r in demand if {r['a'], r['b']} == set(pair)), None)
        if not dr:
            continue
        annual = float(dr['observed']) if scenario == 'base' and dr['observed'] and dr['observed_coverage'] != 'airline_group' else float(dr['pax_base' if scenario == 'base' else 'pax_cautious'])
        dem = annual / (2 * AA['weeks_per_year'])
        L = dict(a=pair[0], b=pair[1], dem=dem, km=float(dr['km']), competitive=dr['direct_now'] == 'True', south=False)
        F = sum(int(r['freq_week_each_way']) for r in rs)
        pooled = min(dem * ns['leg_share'](L, F, AA), F * AA['seats'] * AA['lf_max']) * 2 * AA['weeks_per_year']
        isolated = sum(min(dem * ns['leg_share'](L, int(r['freq_week_each_way']), AA), int(r['freq_week_each_way']) * AA['seats'] * AA['lf_max']) * 2 * AA['weeks_per_year'] for r in rs)
        exported = sum(int(r['pax_year_segments']) for r in rs)
        assert abs(exported - pooled) <= len(rs)
        pool_rows.append(dict(scenario=scenario, pair='-'.join(pair), programs=len(rs), frequency_each_way_week=F,
                              annual_input_segments_both_directions=annual, isolated_same_programs=isolated,
                              pooled_formula=pooled, exported_sum_rounded=exported, unit='annual passenger-segments, both directions'))
table('shared_pair_examples.csv', pool_rows)

L = dict(a='B', b='X', dem=1000., km=1200., competitive=False, south=False)
sel = [('B','X','Y',3,[L]), ('B','X','Z',3,[dict(L)])]
res = ns['joint'](sel)
actual = sum(r[8][0]['carried_dir_week'] for r in res)
expected = min(1000 * ns['leg_share'](L, 6, A), 6 * A['seats'] * A['lf_max'])
assert abs(actual - expected) < 1e-9

class FixtureDemand:
    """Synthetic geography and annual segment-like inputs; not observed markets."""
    def km(self, a, b): return 1000. if 'H' in (a,b) else 1600.
    def green(self, a, b): return 10000.
    def get(self, a, b, scenario): return 10400.
    def south(self, a, b): return False
    def has_direct(self, a, b): return False

S, r = ns['hub_network']('H', FixtureDemand(), A, 'base', ['X','Y'])
legs, transfers, hours, cost, revenue, local_od, transfer_od, flights = r
local_revenue = sum(2 * l['local_carried'] * ns['fare'](A,l['km']) for l in legs.values())
through_revenue = sum(2 * t * ns['fare'](A,km) * A['transfer_fare_factor'] for x,y,km,t in transfers)
assert transfer_od > 0 and abs(revenue-local_revenue-through_revenue)<1e-7
assert abs(sum(2*l['carried_dir_week'] for l in legs.values()) - local_od - 2*transfer_od)<1e-7

import numpy as np
import pandas as pd
scorepath = P / 'inputs' / LATEST / 'src/longlist_score.py'
spec = importlib.util.spec_from_file_location('pinned_score', scorepath)
scorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scorer)
j = json.loads((P/'inputs'/LATEST/'data/processed/criteria.json').read_text())
ll = pd.read_csv(P/'inputs'/LATEST/'data/processed/longlist.csv').set_index('iata')
ll['dist_bases_km'] = ll[['dist_msk_km','dist_ekb_km']].min(axis=1)
sc = scorer.scales(j['criteria'],j['values'])
w = pd.Series({c['key']: c['weight'] for c in j['criteria']})
score_checks=[]
for minimum,strict,name in [(0,False,'longlist_scores.csv'),(500,False,'longlist_scores_min500.csv'),(500,True,'longlist_scores_min500_strict.csv')]:
    ids=[i for i in ll.index if ll.loc[i,'dist_bases_km']>=minimum and not(strict and j['values'][i].get('rw_support',{}).get('v')==1)]
    z,lo,hi,unknown,weak = scorer.tables(ids,j['criteria'],j['values'],sc)
    s=scorer.score(z,w)
    exp=list(csv.DictReader((P/'inputs'/LATEST/'data/processed'/name).open()))
    order=list(s.iloc[np.argsort(-s.to_numpy(),kind='stable')].index)
    assert order==[r['iata'] for r in exp]
    assert all(abs(float(s[r['iata']])-float(r['score']))<=0.000501 for r in exp)
    score_checks.append(dict(mode=name,rows=len(exp),top3=order[:3],status='PASS_center_scores_and_order'))

weatherpath=P/'inputs'/LATEST/'src/catchment_extra.py'
wtree=ast.parse(weatherpath.read_text())
wns=dict(pd=pd)
exec(compile(ast.Module(body=[n for n in wtree.body if isinstance(n,ast.FunctionDef) and n.name=='weather_counts'],type_ignores=[]),str(weatherpath),'exec'),wns)
weather=wns['weather_counts']([('2024-01-01',-9999,-9999),('2024-01-02',-210,130)],-20,12)
assert weather['valid_joint_days']==1 and weather['either']==1 and weather['record_days']==2
checks=dict(scope='SCOPED_OFFLINE_FUNCTIONS_AND_EXPORTED_CSV; NOT_FULL_MODEL_ACCEPTANCE',
    source_sha=LATEST, exact_function_extraction='AST; executable function bodies unchanged; module IO excluded',
    shared_pair_fixture=dict(carried_dir_week=actual,expected=expected,status='PASS'),
    exported_shared_pairs=dict(checked=len(pool_rows),status='PASS_with_individual_row_rounding'),
    single_through_fare_fixture=dict(synthetic=True,local_od_week_both=local_od,transfer_od_week_both=transfer_od,
        local_revenue_rub_week=local_revenue,through_revenue_rub_week=through_revenue,total_revenue_rub_week=revenue,status='PASS'),
    summary_arithmetic=dict(rows=len(money),status='PASS_with_independent_rounding_tolerance_1'),
    longlist=score_checks,weather_sentinel=dict(result=weather,status='PASS'),
    full_network_replay='NOT_RUN: bounded scope; no raw staging or model-wide execution',
    od_fit_refit='NOT_RUN: coefficients and exported diagnostics inspected; no raw/model-wide replay',
    weather_archive_replay='NOT_RUN: no archive staging; function fixture and exported coverage only',
    optimizer_global_optimality='NOT_ESTABLISHED: greedy; standalone top-400 shortlist and fixed standalone frequencies',
    dependencies=dict(python=sys.version,numpy=np.__version__,pandas=pd.__version__))
greedy = ns['direct_network'](FixtureDemand(), A, 'base', ['X','Y','Z'])
assert len(greedy) == 3
groupped = {}
for triangle in greedy:
    for leg in triangle[8]:
        groupped.setdefault(tuple(sorted((leg['a'],leg['b']))),[]).append(leg)
for pair, members in groupped.items():
    f = sum(l['freq'] for l in members)
    expected = min(members[0]['dem']*ns['leg_share'](members[0],f,A), f*A['seats']*A['lf_max'])
    assert abs(sum(l['carried_dir_week'] for l in members)-expected)<1e-7
checks['greedy_fixture'] = dict(synthetic=True,triangles=len(greedy),physical_pairs=len(groupped),
    status='PASS_pooled_final_flows; NOT_global_optimality_or_full_selection_replay')
# Expose retained strict-comparison rank bug only in an exact-tie counterexample.
tie_w = w*0
tie_w['ssj_ops']=1
tz,ta,tb,_,_ = scorer.tables(list(ll.index),j['criteria'],j['values'],sc)
tie_lo,tie_hi = scorer.score(ta,tie_w),scorer.score(tb,tie_w)
tie_worst=[1+int((tie_hi.drop(i)>tie_lo[i]).sum()) for i in ll.index]
assert tie_worst==[1]*len(ll)
checks['rank_tie_counterexample'] = dict(weights={'ssj_ops':1,'all_other_weights':0},
    reported_worst_ranks=tie_worst,stable_order_actual_ranks=list(range(1,len(ll)+1)),
    status='CONFIRMED_RETAINED_DEFECT_arbitrary_weights; NOT_default_top3_change')
write_json('checks.json',checks)

manifest=[]
for f in sorted((P/'inputs').rglob('*')):
    if not f.is_file(): continue
    rel=f.relative_to(P/'inputs'); sha=rel.parts[0]; path='/'.join(rel.parts[1:])
    grain = 'source code/document or parameter definition'
    if path.endswith('.csv'):
        rows=list(csv.DictReader(io.StringIO(f.read_text())))
        grain={'network_summary.csv':'scenario x alternative network; year, both directions; money RUB million',
               'network_routes.csv':'scenario x program x physical airport pair; annual passenger segments, both directions',
               'od_pairs.csv':'unordered airport pair; annual modeled end-to-end journeys, both directions',
               'demand_pairs.csv':'unordered airport pair; annual route passenger-segments, both directions',
               'catchment_extra.csv':'airport catchment; weather daily field coverage, 2023-2024',
               'longlist.csv':'candidate airport; mixed indicators, separate periods and units'}.get(f.name,'CSV rows with units and periods in header/source; see report')
        count=len(rows)
    else: count=None
    author = 'night coordinator / root package' if sha == CHECKOUT else 'kiruha355 / Nastya (package owner); external copied evidence retains its original attribution'
    manifest.append(dict(source_sha=sha,path=path,author=author,
                         sha256=hashlib.sha256(f.read_bytes()).hexdigest(),bytes=f.stat().st_size,rows=count,grain=grain))
write_json('source_manifest.json',manifest)
diff=subprocess.check_output(['git','diff',BASE,LATEST,'--','src/network_model.py','src/od_model.py','src/longlist_score.py','src/catchment_extra.py','src/build_criteria.py','src/demand_model.py','src/update.py','data/assumptions/longlist_weights.csv','data/assumptions/network.csv','data/assumptions/demand.csv','data/manual/pax_2025_overrides.csv'])
(P/'reviewed_diff.patch').write_bytes(diff)
print(json.dumps(checks,ensure_ascii=False,indent=2))
