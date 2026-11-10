#!/usr/bin/env python3
"""MR08 independent oracle. Stdlib, exact Git blobs, no author numeric imports.

The numerical allocator is reconstructed from the declared booking/accounting
contract. Affine cells are independently certified by intersecting every active
branch inequality at an interior point, then recursively covering remaining
gaps. Author affine rows are checked only after our partition is constructed.
Only the four adapter helper functions are AST-loaded for mutation cross-checks;
no author main, check_package, demand, or boundary code is executed.
"""
import ast
import collections
import copy
import csv
import dataclasses
import hashlib
import io
import json
import math
from pathlib import Path
import random
import subprocess

OUT = Path(__file__).resolve().parent
METHODS = 'abb1c76254d2d4e3cf9edd5c345b9cdb224f6abe'
ROOT = 'context/23_night_run_20261110/methods/'
CIRI = '93fa5cf4a10ab67e05c93d19fc5375fc58ef9299'
NASTYA = '2f03b693a62c219e9475fcd1e26295039f6a49d7'
REPAIR = '27740ffea0821aa404ecd1013d1bb141613261f3'
SJR = '944b16ac2dcde846e29dac2d47e11e5143f9fc2b'
S = 'inputs/set001/tsiri_93fa/'
N = 'inputs/set001/nastya_2f03/'
R = 'inputs/model-repair-001/proposed_common_view/'
RUN = 'runs/common_demand_v1/'
A = 'runs/adapter_v1/'
MANIFEST = {}
COUNTS = collections.Counter()
MAX_DELTA = collections.defaultdict(float)
FIELD = 'contribution_before_base_fleet_opportunity'


def blob(path, commit=METHODS, prefix=ROOT, grain=None):
    full = prefix + path
    data = subprocess.check_output(['git', 'show', f'{commit}:{full}'])
    previous=MANIFEST.get((commit,full),{})
    MANIFEST[commit, full] = dict(previous,commit=commit, path=full, bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(), grain=grain or previous.get('grain','source code or document'), access='git show exactSHA:path')
    return data


def rows(path, **kwargs):
    if 'grain' not in kwargs:
        basename=Path(path).name
        kwargs['grain']={
            'itinerary.csv':'model x input set x run x candidate x scenario x dated itinerary',
            'itinerary_leg.csv':'itinerary x ordered physical leg incidence',
            'capacity_allocation.csv':'itinerary x ordered physical leg seat use',
            'physical_leg.csv':'model x input set x run x candidate x scenario x dated flight',
            'money_ledger.csv':'model x run x candidate x scenario x primitive money entry',
            'qualified_money_ledger.csv':'unchanged primitive money entries; flight metadata qualified by unique full leg key',
            'evaluation_summary.csv':'model x input set x run x candidate x scenario; annual and weekly fields remain separate',
            'market_pool.csv':'model x run x candidate x scenario x directed endpoint market',
            'candidate_register.csv':'model x input set x run x candidate x scenario',
            'demand_mapping.csv':'candidate x scenario x unordered pair x C/N demand recipe',
            'affine_regions.csv':'candidate x scenario x recipe x affine parameter interval',
            'exact_demand_boundaries.csv':'candidate x scenario x recipe; zero crossings and extrema of fixed rule',
            'recipe_rank_boundaries.csv':'scenario x candidate pair x demand-blend coordinate',
            'summary.csv':'candidate x scenario x recipe x demand multiplier; RUB per model week',
            'itinerary_at_unit_scale.csv':'candidate x scenario x recipe x dated itinerary',
            'money_metadata_lineage.csv':'original money row x unique physical-leg reference',
            'market_publication_context.csv':'candidate x scenario x actually exported directed market x publication incidence',
            'publication_coverage_summary.csv':'candidate x itinerary role; actual exported directed market denominator',
            'table_mapping.csv':'logical common table x immutable source table x namespace',
        }.get(basename,'CSV row; definition given by column names and exact immutable path')
    result = list(csv.DictReader(io.StringIO(blob(path, **kwargs).decode('utf-8-sig'))))
    MANIFEST[kwargs.get('commit',METHODS),kwargs.get('prefix',ROOT)+path]['rows'] = len(result)
    return result


def js(path, **kwargs):
    return json.loads(blob(path, **kwargs))


def write(name, data):
    if name.endswith('.json'):
        (OUT/name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    else:
        data = list(data)
        with (OUT/name).open('w', newline='') as f:
            w = csv.DictWriter(f, list(dict.fromkeys(k for r in data for k in r)))
            w.writeheader()
            w.writerows(data)


def eq(actual, expected, group, tol=2e-6):
    delta = abs(float(actual)-float(expected))
    COUNTS[group] += 1
    MAX_DELTA[group] = max(MAX_DELTA[group], delta)
    assert math.isfinite(delta) and delta <= tol, (group, actual, expected, delta)


def check(condition, group):
    COUNTS[group] += 1
    assert condition, group


def pair(a, b):
    return '-'.join(sorted((a, b)))


def flight_cost(minutes, p):
    hours = float(minutes)/60
    fuel = (p['fuel_t_per_hour']*hours + p['fuel_t_per_cycle'])*(p['fuel_rub_per_t']+p['fuel_uplift_rub_per_t'])
    hourly = hours*sum(p[k] for k in ['mro_rub_per_hour', 'crew_rub_per_hour', 'navigation_rub_per_hour'])
    ground = (49.45*1052+19300+8100+16668)*p['airport_factor']
    ice = p['deicing_probability']*p['deicing_operation_rub']
    return fuel+hourly+ground+ice


def prepare(sales, p, scenario, assumptions):
    frequency = collections.Counter((s['origin'], s['destination']) for s in sales)
    incumbent_pairs = {pair(s['origin'], s['destination']) for s in sales if s['known_direct_RW_capacity'] and float(s['known_direct_RW_capacity']) > 0}
    result = []
    for s in sales:
        od = s['origin'], s['destination']
        transfer = s['transfer'] == 'True'
        k = frequency[od]
        capture = assumptions['local_peak'][scenario]*(1-math.exp(-k/p['frequency_scale']))
        if transfer:
            capture *= .65
        migration = assumptions['known_incumbent_migration'][scenario] if pair(*od) in incumbent_pairs else (.05 if scenario == 'base' else .1)
        fare = float(s['fare_once'])
        old_fare = fare/(p['transfer_fare_factor'] if transfer else 1)*p['old_RW_fare_ratio']
        result.append(dict(od=od, market=pair(*od), transfer=transfer, day=int(s['day']),
            legs=tuple(s['flight_ids'].split(';')), fare=fare, old_fare=old_fare,
            migration=migration, direct_cap=float(s['known_direct_RW_capacity'] or 0),
            capture_per_offer=capture/k, demand=float(s['D'])))
    result.sort(key=lambda o: (o['transfer'], -(o['fare']-o['migration']*o['old_fare']-len(o['legs'])*p['pax_cost'])/len(o['legs']), *o['od'], o['day'], o['legs']))
    return result


def simulate(offers, caps, p, demand=None, minimum=min, migration_scale=1, transfer_first=False):
    """Fresh seats and migration state per call, per directed market, per alternative."""
    available = {r['flight_id']:float(r['capacity_scenario']) for r in caps}
    migration = {o['od']:o['direct_cap'] for o in offers}
    total = collections.defaultdict(lambda: 0)
    details = []
    sequence = sorted(offers, key=lambda o: not o['transfer']) if transfer_first else offers
    for o in sequence:
        D = o['demand'] if demand is None else demand[o['market']]
        wanted = D*o['capture_per_offer']
        trips = minimum([wanted]+[available[i] for i in o['legs']])
        for leg in o['legs']:
            available[leg] -= trips
        can = o['migration']*migration_scale
        old_direct = minimum([trips*can, migration[o['od']]])
        migration[o['od']] -= old_direct
        old_connect = trips*can-old_direct
        values = dict(sold_journeys=trips, transfer_journeys=trips if o['transfer'] else 0,
            segment_pax=trips*len(o['legs']), migrated_RW_total=old_direct+old_connect,
            migrated_RW_direct=old_direct, migrated_RW_unverified_connecting=old_connect,
            gross_revenue=trips*o['fare'], foregone_RW_revenue=(old_direct+old_connect)*o['old_fare'],
            new_pax_variable=trips*len(o['legs'])*p['pax_cost'],
            saved_old_pax_variable=(old_direct+old_connect*2)*p['pax_cost'])
        for name, value in values.items():
            total[name] += value
        details.append(dict(origin=o['od'][0], destination=o['od'][1], day=o['day'],
            flight_ids=';'.join(o['legs']), transfer=o['transfer'], D=D,
            desired=wanted, fare_once=o['fare'], **values))
    total['flight_variable_cost'] = sum(flight_cost(c['block_minutes'], p) for c in caps)
    total['incremental_revenue'] = total['gross_revenue']-total['foregone_RW_revenue']
    total['incremental_operating_cost'] = total['flight_variable_cost']+total['new_pax_variable']-total['saved_old_pax_variable']
    total[FIELD] = total['incremental_revenue']-total['incremental_operating_cost']
    total['net_new_RW_journeys_scenario'] = total['sold_journeys']-total['migrated_RW_total']
    total['load_factor'] = total['segment_pax']/sum(float(c['capacity_scenario']) for c in caps)
    return dict(total), details, available


@dataclasses.dataclass(frozen=True)
class Line:
    a: float
    b: float = 0.
    def __add__(self, other):
        if not isinstance(other, Line): other = Line(other)
        return Line(self.a+other.a, self.b+other.b)
    __radd__ = __add__
    def __neg__(self): return Line(-self.a, -self.b)
    def __sub__(self, other): return self+-other if isinstance(other, Line) else self+-float(other)
    def __rsub__(self, other): return -self+other
    def __mul__(self, other): return Line(self.a*other, self.b*other)
    __rmul__ = __mul__
    def __truediv__(self, other): return self*(1/other)
    def at(self, x): return self.a+self.b*x


class PathCertificate:
    def __init__(self, sample, end):
        self.sample, self.lower, self.upper = sample, 0., end
        self.inequalities = 0
    def minimum(self, options):
        lines = [v if isinstance(v, Line) else Line(v) for v in options]
        chosen = min(lines, key=lambda line:line.at(self.sample))
        for other in lines:
            # chosen-other <= 0 is necessary and sufficient along this branch path.
            delta = chosen-other
            self.inequalities += 1
            if abs(delta.b) < 1e-12:
                assert delta.a <= 1e-7
            elif delta.b > 0:
                self.upper = min(self.upper, -delta.a/delta.b)
            else:
                self.lower = max(self.lower, -delta.a/delta.b)
        return chosen


def partition(offers, caps, p, demands, end):
    """Cover domain using maximal branch-validity cells sampled in gap interiors."""
    gaps, cells = [(0., end)], []
    while gaps:
        lo, hi = gaps.pop()
        if hi-lo < 1e-10: continue
        x = lo+(hi-lo)*.3819660112501051
        cert = PathCertificate(x, end)
        totals, _, _ = simulate(offers, caps, p, demands, minimum=cert.minimum)
        a, b = max(lo, cert.lower), min(hi, cert.upper)
        assert a <= x+1e-8 and b >= x-1e-8 and b-a > 1e-12, (lo,hi,x,a,b)
        cell = dict(left=a, right=b, branch_inequalities=cert.inequalities)
        for label, name in [('contribution', FIELD), ('journeys','sold_journeys'), ('segments','segment_pax'), ('transfers','transfer_journeys')]:
            line = totals[name]
            if not isinstance(line, Line): line = Line(line)
            cell[label+'_intercept'], cell[label+'_slope'] = line.a, line.b
        cells.append(cell)
        if a-lo > 1e-10: gaps.append((lo,a))
        if hi-b > 1e-10: gaps.append((b,hi))
        assert len(cells) < 10000
    cells.sort(key=lambda r:r['left'])
    eq(cells[0]['left'],0,'partition_coverage',1e-8)
    eq(cells[-1]['right'],end,'partition_coverage',1e-8)
    for left,right in zip(cells,cells[1:]):eq(left['right'],right['left'],'partition_coverage',1e-8)
    return cells


def conservation(total, detail, available, caps):
    use, sold, D = collections.Counter(), collections.Counter(), {}
    for r in detail:
        for i in r['flight_ids'].split(';'): use[i] += r['sold_journeys']
        k = r['origin'],r['destination']
        sold[k] += r['sold_journeys']; D[k] = r['D']
        eq(r['gross_revenue'],r['sold_journeys']*r['fare_once'],'single_fare')
    for c in caps:
        i = c['flight_id']
        eq(use[i]+available[i], c['capacity_scenario'],'seat_balance')
        check(available[i] >= -1e-7, 'nonnegative_capacity')
    for k,v in sold.items():check(v <= D[k]+1e-7,'shared_directed_pool')
    eq(sum(use.values()),total['segment_pax'],'segment_conservation')
    eq(total['sold_journeys']+total['transfer_journeys'],total['segment_pax'],'two_legs_one_journey')


def main():
    for p in ['contract.md','briefs/common_comparison_review.md']:
        blob('context/23_night_run_20261110/'+p,commit='f1774e1f66a9483fb618ca6003abd9dc4d8563e1',prefix='',grain='review instructions')
    contract = js('common_demand_contract.json')
    config = js(S+'context/15_team_update/model/configuration.json')
    assumptions = js(S+'context/16_conditional_decision/assumptions.json')
    source_summary = rows(S+'context/21_team_proposals/comparison.csv',grain='candidate x scenario x model week')
    all_sales = rows(S+'context/17_aircraft_route_review/model/sales.csv',grain='profile x candidate x scenario x dated itinerary')
    all_caps = rows(S+'context/17_aircraft_route_review/model/capacity.csv',grain='profile x candidate x scenario x physical flight')
    flights = rows(S+'context/17_aircraft_route_review/model/flights.csv',grain='profile x candidate x physical dated flight')
    nd = rows(N+'data/processed/demand_pairs.csv',grain='unordered airport pair x annual segment-scale proxy')
    nd = {pair(r['a'],r['b']):r for r in nd}
    # Read source definitions, never execute them.
    for f in [S+'scripts/build_team_comparison.py',S+'scripts/build_aircraft_route_review.py',S+'scripts/build_team_proposals.py',S+'scripts/build_conditional_decision.py',N+'src/network_model.py',N+'src/demand_model.py','common_demand.py','common_boundaries.py','common_comparison_readout.md']:
        blob(f)
    # The frozen source copies are compared with the actual author commits.
    frozen_checks=[]
    for local,sha,upstream in [(S+'context/21_team_proposals/comparison.csv',CIRI,'context/21_team_proposals/comparison.csv'),(S+'context/17_aircraft_route_review/model/sales.csv',CIRI,'context/17_aircraft_route_review/model/sales.csv'),(S+'context/17_aircraft_route_review/model/capacity.csv',CIRI,'context/17_aircraft_route_review/model/capacity.csv'),(S+'context/17_aircraft_route_review/model/flights.csv',CIRI,'context/17_aircraft_route_review/model/flights.csv'),(S+'context/15_team_update/model/configuration.json',CIRI,'context/15_team_update/model/configuration.json'),(N+'data/processed/demand_pairs.csv',NASTYA,'data/processed/demand_pairs.csv'),(N+'src/network_model.py',NASTYA,'src/network_model.py')]:
        check(blob(local)==blob(upstream,commit=sha,prefix=''),'frozen_author_bytes')
        frozen_checks.append(dict(local=local,upstream_commit=sha,upstream_path=upstream,equal=True))
    write('frozen_author_checks.json',frozen_checks)
    cases, baselines, independent_sales, cost_rows, mappings, excluded = {}, [], [], [], [], []
    for r in source_summary:
        name,sc = r['network'],r['scenario']; p = config['scenarios'][sc]
        source_key = r['source_profile'],r['source_network']
        ss = [s for s in all_sales if (s['profile'],s['network'],s['scenario'])==(*source_key,sc)]
        cc = [c for c in all_caps if (c['profile'],c['network'],c['scenario'])==(*source_key,sc)]
        ff = [f for f in flights if (f['profile'],f['network'])==source_key]
        capids = [c['flight_id'] for c in cc]; fids = [f['id'] for f in ff]
        check(len(set(capids))==len(cc) and len(set(fids))==len(ff),'unique_flight_capacity_ids')
        check(set(capids)==set(fids)=={i for s in ss for i in s['flight_ids'].split(';')},'complete_flight_capacity_ids')
        fmap={f['id']:f for f in ff}
        for c in cc:
            f=fmap[c['flight_id']]
            check((c['origin'],c['destination'])==(f['origin'],f['destination']),'flight_route')
            eq(c['block_minutes'],f['block_minutes'],'flight_block')
            fc = flight_cost(f['block_minutes'],p)
            eq(fc,c['flight_variable_cost'],'flight_cost_formula')
            cost_rows.append(dict(network=name,scenario=sc,flight_id=c['flight_id'],exported=float(c['flight_variable_cost']),independent=fc))
        offers=prepare(ss,p,sc,assumptions)
        by_pair=collections.defaultdict(set)
        for s in ss:by_pair[pair(s['origin'],s['destination'])].add(float(s['D']))
        check(all(len(v)==1 for v in by_pair.values()),'C_pair_direction_week_support')
        total,detail,remaining=simulate(offers,cc,p)
        conservation(total,detail,remaining,cc)
        source_index={s['flight_ids']:s for s in ss}
        check(len(source_index)==len(ss),'unique_sales_key')
        for item in detail:
            old=source_index[item['flight_ids']]
            for k,v in item.items():
                if k in old and isinstance(v,(float,int)) and not isinstance(v,bool):eq(v,old[k],'baseline_sales')
            independent_sales.append(dict(network=name,scenario=sc,**item))
        for k,v in total.items():
            if k in r:eq(v,r[k],'baseline_summary')
        for c in cc:eq(float(c['capacity_scenario'])-remaining[c['flight_id']],c['occupied'],'baseline_occupied')
        baselines.append(dict(network=name,scenario=sc,itineraries=len(ss),flight_scenario_rows=len(cc),**total))
        C={o['market']:o['demand'] for o in offers};missing=sorted(set(C)-set(nd))
        if missing:
            check(len(missing)==6 and all('ZIA' in k for k in missing),'six_zia_missing_no_mow')
            excluded.append(dict(network=name,scenario=sc,missing_pairs=';'.join(missing)))
            continue
        NN={}
        for k in sorted(C):
            n=nd[k]
            field='observed' if sc=='base' and n['observed'] and n['observed_coverage']!='airline_group' else 'pax_'+sc
            NN[k]=float(n[field])/2/52
            mappings.append(dict(network=name,scenario=sc,pair=k,C_week_direction=C[k],N_field=field,
                N_annual_proxy=float(n[field]),N_week_direction_stress=NN[k],N_coverage=n['observed_coverage'],N_period=n['observed_period'],N_method=n['method']))
        cases[name,sc]=dict(offers=offers,caps=cc,p=p,C=C,N=NN)
    check(sum(r['itineraries'] for r in baselines)==224,'baseline_224_rows')
    check(len(cost_rows)==160 and len(baselines)==8,'baseline_160_flight_rows_8_totals')
    write('independent_baselines.csv',baselines);write('independent_sales.csv',independent_sales)
    write('independent_flight_costs.csv',cost_rows);write('independent_demand_mapping.csv',mappings);write('independent_exclusions.json',excluded)
    advertised_mapping=rows(RUN+'demand_mapping.csv')
    check(len(advertised_mapping)==len(mappings),'all_demand_mapping_rows')
    for mine,old in zip(mappings,advertised_mapping):
        for k,v in mine.items():
            if isinstance(v,float):eq(v,old[k],'demand_mapping_numeric')
            else:check(v==old[k],'demand_mapping_metadata')
    controlled=[]; unit_details=[]
    for (name,sc),case in cases.items():
        for recipe in ['C','N']:
            for scale in contract['probe_multipliers']:
                demand={k:v*scale for k,v in case[recipe].items()}
                total,detail,remaining=simulate(case['offers'],case['caps'],case['p'],demand)
                conservation(total,detail,remaining,case['caps'])
                controlled.append(dict(network=name,scenario=sc,recipe=recipe,multiplier=scale,**total))
                if scale==1:unit_details.extend(dict(network=name,scenario=sc,recipe=recipe,**d) for d in detail)
        # Explicit interleaving of independent alternatives must leave prior state intact.
        before=simulate(case['offers'],case['caps'],case['p'],case['N'])[0]
        for other in reversed(list(cases.values())):
            simulate(other['offers'],other['caps'],other['p'],{k:v*100 for k,v in other['C'].items()})
        after=simulate(case['offers'],case['caps'],case['p'],case['N'])[0]
        check(before==after,'no_state_leak')
    old_summary=rows(RUN+'summary.csv'); old_by={(r['network'],r['scenario'],r['recipe'],float(r['multiplier'])):r for r in old_summary}
    check(len(old_by)==len(old_summary)==len(controlled)==84,'all_controlled_summary_rows')
    for r in controlled:
        old=old_by[r['network'],r['scenario'],r['recipe'],r['multiplier']]
        origin=next(s for s in source_summary if (s['network'],s['scenario'])==(r['network'],r['scenario']))
        fixed=dict(source_commit=CIRI,source_variant='context21_team_proposals',source_profile=origin['source_profile'],source_network=origin['source_network'],
            period_start='2026-12-07',period_end='2026-12-13',price_basis='CIRI_NET_SCENARIO_FARE',tax_basis='EX_RECOVERABLE_VAT_AS_AUTHOR_SCENARIO',
            active_ceiling='4',active_allocated=origin['active_allocated'],reserve_assumption='1',decision_status='AGENT_PROPOSAL')
        check(all(old[k]==v for k,v in fixed.items()),'controlled_fixed_context_metadata')
        for k,v in r.items():
            if k in old and isinstance(v,(float,int)):eq(v,old[k],'controlled_summary')
    old_units=rows(RUN+'itinerary_at_unit_scale.csv');index={(r['network'],r['scenario'],r['recipe'],r['flight_ids']):r for r in old_units}
    check(len(index)==len(old_units)==len(unit_details)==384,'all_unit_itinerary_rows')
    for r in unit_details:
        old=index[r['network'],r['scenario'],r['recipe'],r['flight_ids']]
        for k,v in r.items():
            if k in old and isinstance(v,(float,int)) and not isinstance(v,bool):eq(v,old[k],'unit_itineraries')
    write('independent_summary.csv',controlled);write('independent_unit_itineraries.csv',unit_details)
    boundary_checks(cases)
    adapter_checks(source_summary)
    source_holds()
    write('independent_results.json',dict(status='PASS_SCOPED_INDEPENDENT_NUMERICS',review='MR08',methods_commit=METHODS,
        checks=dict(COUNTS),max_abs_delta=dict(MAX_DELTA),author_numerical_code_executed=False,
        author_adapter_helpers_executed='AST-only qualify_flight_money/validate_tables/key/near for mutation comparison',
        observed_demand=False,full_budget=False,source_lineage_acceptance='HOLD_PRESERVED'))
    write('source_manifest.json',dict(entries=list(MANIFEST.values()),source_access='EXACT_GIT_SHOW_ONLY',live_worktree_inputs=False))
    print(json.dumps(dict(status='PASS',numeric_and_semantic_checks=sum(COUNTS.values()),source_blobs=len(MANIFEST),checks=dict(COUNTS)),indent=2))


def boundary_checks(cases):
    cells_all=[];curves={};bounds=[];points=[]
    rng=random.Random(230810)
    for (name,sc),case in cases.items():
        for recipe in ['C','N','C_TO_N_BLEND']:
            if recipe=='C_TO_N_BLEND':
                demands={k:Line(v,case['N'][k]-v) for k,v in case['C'].items()};end=1.
            else:
                demands={k:Line(0,v) for k,v in case[recipe].items()}
                cm={c['flight_id']:float(c['capacity_scenario']) for c in case['caps']}
                end=max(cm[o['legs'][0]]/(case[recipe][o['market']]*o['capture_per_offer']) for o in case['offers'] if not o['transfer'])
            cells=partition(case['offers'],case['caps'],case['p'],demands,end)
            curves[name,sc,recipe]=(cells,demands,end)
            cells_all.extend(dict(network=name,scenario=sc,recipe=recipe,**r) for r in cells)
            roots=[];extrema=[]
            for i,r in enumerate(cells):
                a,b=r['contribution_intercept'],r['contribution_slope']
                if abs(b)>1e-10:
                    root=-a/b
                    if r['left']-1e-9<=root<=r['right']+1e-9:roots.append(root)
                for x in [r['left'],r['right']]:extrema.append((a+b*x,x))
                for x in [r['left'],r['right'],(r['left']+r['right'])/2,r['left']+(r['right']-r['left'])*rng.random()]:
                    totals,_,_=simulate(case['offers'],case['caps'],case['p'],{k:v.at(x) for k,v in demands.items()})
                    for field,target in [('contribution',FIELD),('journeys','sold_journeys'),('segments','segment_pax'),('transfers','transfer_journeys')]:
                        eq(totals[target],r[field+'_intercept']+r[field+'_slope']*x,'independent_cell_numeric',3e-5)
                # One-sided samples at every own breakpoint, with the correct adjacent cell.
                for x in [max(0,r['left']-1e-7),min(end,r['right']+1e-7)]:
                    totals,_,_=simulate(case['offers'],case['caps'],case['p'],{k:v.at(x) for k,v in demands.items()})
                    cell=next(c for c in cells if c['left']-1e-12<=x<=c['right']+1e-12)
                    eq(totals[FIELD],cell['contribution_intercept']+cell['contribution_slope']*x,'breakpoint_both_sides',3e-5)
                    points.append(dict(network=name,scenario=sc,recipe=recipe,x=x,contribution=totals[FIELD]))
            best,best_x=max(extrema)
            unique_roots=sorted({round(v,10) for v in roots})
            for root in unique_roots:
                for x in [root-1e-7,root,root+1e-7]:
                    totals,_,_=simulate(case['offers'],case['caps'],case['p'],{k:v.at(x) for k,v in demands.items()})
                    if x<root:check(totals[FIELD]<0,'first_zero_left_negative')
                    elif x>root:check(totals[FIELD]>0,'first_zero_right_positive')
                    else:eq(totals[FIELD],0,'zero_by_numeric_simulation',.005)
            bounds.append(dict(network=name,scenario=sc,recipe=recipe,domain_end=end,region_count=len(cells),
                zero_crossings=';'.join(format(x,'.12g') for x in unique_roots),maximum_contribution=best,maximum_at=best_x,
                contribution_at_domain_end=extrema[-1][0]))
            if recipe!='C_TO_N_BLEND':
                for factor in [1.01,2,1000]:
                    totals,_,_=simulate(case['offers'],case['caps'],case['p'],{k:v*end*factor for k,v in case[recipe].items()})
                    eq(totals[FIELD],extrema[-1][0],'saturation_tail',3e-5)
                    eq(totals['transfer_journeys'],0,'saturation_no_transfers')
    old=rows(RUN+'affine_regions.csv')
    check(len(old)==151,'author_151_regions')
    check(len(cells_all)==151,'independent_151_regions')
    for r in old:
        name,sc,recipe=r['network'],r['scenario'],r['recipe'];case=cases[name,sc]
        cells,demands,end=curves[name,sc,recipe]
        lo,hi=float(r['left']),float(r['right'])
        for x in [lo,hi,(lo+hi)/2,lo+(hi-lo)*.13,lo+(hi-lo)*.87]:
            totals,_,_=simulate(case['offers'],case['caps'],case['p'],{k:v.at(x) for k,v in demands.items()})
            for field,target in [('contribution',FIELD),('journeys','sold_journeys'),('segments','segment_pax'),('transfers','transfer_journeys')]:
                eq(totals[target],float(r[field+'_intercept'])+float(r[field+'_slope'])*x,'author_cell_vs_independent_simulation',3e-5)
        # Compare values and slopes at every intersection with our independently certified cells.
        for c in cells:
            a,b=max(lo,c['left']),min(hi,c['right'])
            if b-a>1e-8:
                for f in ['contribution','journeys','segments','transfers']:
                    eq(r[f+'_slope'],c[f+'_slope'],'affine_slope_certificate',3e-5)
                    eq(float(r[f+'_intercept'])+float(r[f+'_slope'])*(a+b)/2,c[f+'_intercept']+c[f+'_slope']*(a+b)/2,'affine_value_certificate',3e-5)
    old_bounds=rows(RUN+'exact_demand_boundaries.csv');idx={(r['network'],r['scenario'],r['recipe']):r for r in old_bounds}
    for r in bounds:
        old=idx[r['network'],r['scenario'],r['recipe']]
        for k in ['domain_end','maximum_contribution','contribution_at_domain_end']:eq(r[k],old[k],'boundary_summary',3e-5)
        check(r['zero_crossings']==old['zero_crossings'],'all_zero_crossings')
    rank=[];rank_intervals=[]
    def value(name,sc,x):
        case=cases[name,sc]
        d={k:v*(1-x)+case['N'][k]*x for k,v in case['C'].items()}
        return simulate(case['offers'],case['caps'],case['p'],d)[0][FIELD]
    for sc in ['base','cautious']:
        diff=lambda x:value('D_SVX8',sc,x)-value('H_UFA_4',sc,x)
        dc=curves['D_SVX8',sc,'C_TO_N_BLEND'][0];hc=curves['H_UFA_4',sc,'C_TO_N_BLEND'][0]
        knots=sorted({0.,1.}|{r['left'] for r in dc+hc}|{r['right'] for r in dc+hc})
        affine_roots=[]
        for lo,hi in zip(knots,knots[1:]):
            if hi-lo<1e-10:continue
            mid=(lo+hi)/2
            dd=next(r for r in dc if r['left']-1e-12<=mid<=r['right']+1e-12)
            hh=next(r for r in hc if r['left']-1e-12<=mid<=r['right']+1e-12)
            intercept=dd['contribution_intercept']-hh['contribution_intercept'];slope=dd['contribution_slope']-hh['contribution_slope']
            rank_intervals.append(dict(scenario=sc,left=lo,right=hi,difference_intercept=intercept,difference_slope=slope,
                delta_left=intercept+slope*lo,delta_right=intercept+slope*hi))
            eq(diff(mid),intercept+slope*mid,'rank_interval_certificate',3e-5)
            if abs(slope)>1e-10 and lo-1e-10<=-intercept/slope<=hi+1e-10:affine_roots.append(-intercept/slope)
            if sc=='cautious':check(max(intercept+slope*lo,intercept+slope*hi)<0,'cautious_exact_no_crossing')
        check(len(affine_roots)==(1 if sc=='base' else 0),'rank_all_affine_roots')
        if diff(0)*diff(1)<0:
            lo,hi=0.,1.
            for _ in range(70):
                mid=(lo+hi)/2
                if diff(mid)>0:hi=mid
                else:lo=mid
            x=(lo+hi)/2
            eq(x,affine_roots[0],'rank_bisection_vs_affine',1e-12)
            rank.append(dict(scenario=sc,alpha=x,contribution_a=value('D_SVX8',sc,x),contribution_b=value('H_UFA_4',sc,x),delta_left=diff(x-1e-7),delta_right=diff(x+1e-7)))
        else:
            check(all(diff(i/1000)<0 for i in range(1001)),'cautious_no_rank_crossing')
    author_rank=rows(RUN+'recipe_rank_boundaries.csv');check(len(rank)==len(author_rank)==1,'one_rank_boundary')
    eq(rank[0]['alpha'],author_rank[0]['alpha'],'rank_alpha',1e-12)
    eq(rank[0]['contribution_a'],-3168101.77,'rank_tie_rub_rounded',.01)
    eq(rank[0]['contribution_a'],rank[0]['contribution_b'],'rank_tie')
    counter=[]
    case=cases['D_SVX8','base'];sat={k:v*1000 for k,v in case['C'].items()}
    for migration in [1,0]:
        t,_,_=simulate(case['offers'],case['caps'],case['p'],sat,migration_scale=migration)
        counter.append(dict(probe='D_SVX8_saturated_migration',migration_scale=migration,contribution=t[FIELD]))
    check(counter[0]['contribution']<0<counter[1]['contribution'],'migration_is_material_to_no_zero_claim')
    for name in ['H_UFA_4','H_UFA_8']:
        case=cases[name,'base'];d={k:v*3 for k,v in case['C'].items()}
        for priority in [False,True]:
            t,_,_=simulate(case['offers'],case['caps'],case['p'],d,transfer_first=priority)
            counter.append(dict(probe=name+'_priority_at_C_times3',transfer_first=priority,contribution=t[FIELD],transfer_journeys=t['transfer_journeys']))
        check(counter[-2]['contribution']>0>counter[-1]['contribution'],'local_first_is_material_to_zero_claim')
    write('independent_affine_regions.csv',cells_all);write('independent_boundaries.csv',bounds)
    write('independent_boundary_sides.csv',points);write('independent_rank_boundary.json',rank)
    write('independent_rank_intervals.csv',rank_intervals)
    write('assumption_counterexamples.json',counter)


def adapter_checks(source_summary):
    its=rows(R+'itinerary.csv');links=rows(R+'itinerary_leg.csv');legs=rows(R+'physical_leg.csv');alloc=rows(R+'capacity_allocation.csv')
    money=rows(R+'money_ledger.csv');summary=[r for r in rows(R+'evaluation_summary.csv') if r['model_id']=='ciri_route_model']
    qualified=rows(A+'qualified_money_ledger.csv');lineage=rows(A+'money_metadata_lineage.csv')
    receipt=js('inputs/model-repair-001/receipt.json')
    for path in ['itinerary.csv','itinerary_leg.csv','physical_leg.csv','capacity_allocation.csv','money_ledger.csv','evaluation_summary.csv','market_pool.csv','resource_ledger.csv']:
        local=R+path
        entry=next(r for r in receipt['files'] if r['path']==local)
        check(entry['source_commit']==REPAIR,'repair_receipt_pin')
        check(blob(local)==blob(entry['source_path'],commit=REPAIR,prefix='',grain='original model-repair table; see normalized schema'),'repair_frozen_bytes')
        check(hashlib.sha256(blob(local)).hexdigest()==entry['sha256'],'repair_receipt_hash')
    check(len(its)==224 and len(legs)==160 and len(money)==1056,'adapter_row_counts')
    check(len(money)==len(qualified),'qualified_row_count_unchanged')
    fields=['author_ref','input_set_id','run_id','mode','period_start','period_end','direction_scope','market_unit','currency','price_basis','tax_basis','value_status','acceptance_scope']
    def group(r):return tuple(r[k] for k in ['model_id','source_commit','input_set_id','run_id','candidate_id','profile','scenario_id'])
    anchorfields=['model_id','source_commit','candidate_id','profile','scenario_id','physical_leg_id']
    changes=[]
    for i,(old,new) in enumerate(zip(money,qualified),2):
        changed={k for k in old if old[k]!=new[k]}
        if old['entry']=='flight_variable_cost':
            matches=[l for l in legs if all(l[k]==old[k] for k in anchorfields)]
            check(len(matches)==1,'qualification_unique_full_leg_key')
            leg=matches[0];ss=[s for s in summary if group(s)==group(leg)]
            check(len(ss)==1,'qualification_unique_summary')
            expected=dict(old)
            for f in fields:
                v=leg.get(f) or ss[0].get(f)
                check(bool(v),'qualification_nonempty_metadata')
                if old[f]:check(old[f]==v,'qualification_existing_metadata_preserved')
                else:expected[f]=v
            check(expected==new,'qualified_projection_matches_own_join')
            changes.append(dict(source_row=i,physical_leg_id=old['physical_leg_id'],filled_fields=';'.join(f for f in fields if f in changed)))
        else:check(old==new,'nonflight_money_unchanged')
        check(changed<=set(fields),'amounts_and_keys_unchanged')
    check(len(changes)==len(lineage)==160,'160_qualified_rows')
    for a,b in zip(changes,lineage):
        check(str(a['source_row'])==b['source_row'] and a['physical_leg_id']==b['physical_leg_id'] and a['filled_fields']==b['filled_fields'],'metadata_lineage_rows')
    own_adapter_gate(its,links,legs,alloc,qualified,summary)
    # Execute only four pure, pinned adapter functions, not its main or save.
    source=blob('build_comparison_adapter.py').decode();tree=ast.parse(source)
    tree.body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'key','near','qualify_flight_money','validate_tables'}]
    ns={'collections':collections};exec(compile(tree,'frozen_adapter_helpers','exec'),ns)
    projected,_=ns['qualify_flight_money'](copy.deepcopy(money),copy.deepcopy(legs),copy.deepcopy(summary))
    check(projected==qualified,'actual_author_qualification_matches')
    probes=[]
    for label,ll,mm in [('missing_physical_leg',legs[1:],qualified),('duplicate_physical_leg',legs+[legs[0]],qualified),('per_leg_cost_shift',[dict(r,flight_variable_cost_rub=str(float(r['flight_variable_cost_rub'])+1000000)) if i==0 else r for i,r in enumerate(legs)],qualified),('duplicate_flight_cost',legs,qualified+[next(r for r in qualified if r['entry']=='flight_variable_cost')])]:
        statuses={}
        for validator,f in [('independent',own_adapter_gate),('pinned_author',ns['validate_tables'])]:
            saved_counts,saved_max=dict(COUNTS),dict(MAX_DELTA)
            try:f(its,links,ll,alloc,mm,summary)
            except (AssertionError,KeyError):statuses[validator]='REJECTED'
            else:statuses[validator]='ACCEPTED'
            COUNTS.clear();COUNTS.update(saved_counts);MAX_DELTA.clear();MAX_DELTA.update(saved_max)
        check(set(statuses.values())=={'REJECTED'},'four_mutation_probes_rejected')
        probes.append(dict(probe=label,**statuses))
    for label,ll in [('missing_anchor',legs[1:]),('ambiguous_anchor',legs+[legs[0]])]:
        try:ns['qualify_flight_money'](money,ll,summary)
        except AssertionError:status='REJECTED'
        else:status='ACCEPTED'
        check(status=='REJECTED','metadata_anchor_mutations')
        probes.append(dict(probe=label,pinned_author=status))
    write('independent_adapter_mutations.csv',probes);write('independent_metadata_lineage.csv',changes)
    signs={'gross_revenue':1,'foregone_RW_revenue':-1,'new_pax_variable':-1,'saved_old_pax_variable':1,'flight_variable_cost':-1}
    ledger=[]
    for s in summary:
        mm=[r for r in qualified if group(r)==group(s)]
        sums=collections.Counter()
        for r in mm:
            check(int(r['sign_in_contribution'])==signs[r['entry']],'ledger_sign')
            check(float(r['amount_rub'])>=0,'ledger_nonnegative_amounts')
            sums[r['entry']]+=float(r['amount_rub'])
        for entry,v in sums.items():eq(v,s[entry],'ledger_included_once')
        amount=sum(sums[k]*signs[k] for k in sums)
        eq(amount,s[FIELD],'ledger_total')
        ledger.append(dict(candidate=s['candidate_id'],scenario=s['scenario_id'],**sums,contribution=amount))
    write('independent_money_reconciliation.csv',ledger)
    candidate=rows('inputs/data-bridge-001/normalized/candidate_register.csv')
    mapping=rows(A+'table_mapping.csv')
    historical=rows('itinerary.csv',commit='abc09bbb8e62d3513749b60b252d4521997acfc3',prefix='context/23_night_run_20261110/data_bridge/normalized/')
    # The historical normalized file may contain other models; count conditional16 only.
    conditional=[r for r in historical if 'ciri' in r['model_id'].lower()]
    check(len(conditional)==860,'conditional16_860_separate')
    check(any('860conditional16 !=224context21' in r['key_rule'] for r in mapping),'mapping_variant_namespace')
    h4={r['origin'] for r in its if r['candidate_id']=='H_UFA_4'}|{r['destination'] for r in its if r['candidate_id']=='H_UFA_4'}
    check(h4-{'UFA'}=={'GSV','MRV','NJC','OMS'},'context21_H4_leaf_identity')
    selected=js(S+'context/17_aircraft_route_review/model/selected_networks.json')
    other=selected['RELAXED_SAME_INPUTS_100|H_UFA_4']['leaves']
    check(set(other)!=h4-{'UFA'} and 'GOJ' in other and 'MRV' not in other,'same_name_different_H4_not_joined')
    resources=rows(R+'resource_ledger.csv');resource_checks=[]
    for rr in resources:
        old=next(s for s in source_summary if (s['network'],s['scenario'])==(rr['candidate_id'],rr['scenario_id']))
        eq(rr['actually_allocated'],old['active_allocated'],'resource_actual_use_preserved')
        eq(rr['active_ceiling'],4,'resource_common_ceiling')
        eq(rr['reserve_assumption'],1,'resource_reserve')
        eq(rr['block_hours'],old['weekly_block_hours'],'resource_hours')
        resource_checks.append(dict(candidate=rr['candidate_id'],scenario=rr['scenario_id'],active=int(rr['actually_allocated']),ceiling=4,reserve=1,block_hours=float(rr['block_hours'])))
    write('independent_resource_scope.csv',resource_checks)
    write('adapter_variant_scope.json',dict(context21_itineraries=len(its),conditional16_itineraries=len(conditional),context21_H4_leaves=sorted(h4-{'UFA'}),same_name_is_not_key=True,full_budget=None,included_in='Five mutually exclusive primitive entries; incremental_revenue/operating_cost/contribution are derived, never booked again; old flight cancellation savings excluded'))


def own_adapter_gate(its,links,legs,alloc,money,summary):
    key=lambda r:tuple(r[k] for k in ['model_id','source_commit','input_set_id','run_id','candidate_id','profile','scenario_id'])
    groups={key(r) for r in its}
    assert all({key(r) for r in table}==groups for table in [links,legs,alloc,money,summary])
    for g in {key(r) for r in its}:
        ii=[r for r in its if key(r)==g];ll=[r for r in legs if key(r)==g];xx=[r for r in links if key(r)==g];aa=[r for r in alloc if key(r)==g];mm=[r for r in money if key(r)==g];ss=[r for r in summary if key(r)==g]
        assert len(ss)==1
        im={r['itinerary_id']:r for r in ii};lm={r['physical_leg_id']:r for r in ll}
        assert len(im)==len(ii) and len(lm)==len(ll)
        assert {r['physical_leg_id'] for r in xx}==set(lm)
        assert {r['itinerary_id'] for r in xx}==set(im)
        lk=lambda r:(r['itinerary_id'],r['sequence'],r['physical_leg_id'],r['seats'])
        assert collections.Counter(map(lk,xx))==collections.Counter(map(lk,aa))
        assert len(xx)==len({(r['itinerary_id'],r['sequence']) for r in xx})
        occupancy=collections.Counter()
        for id,it in im.items():
            path=sorted([x for x in xx if x['itinerary_id']==id],key=lambda x:int(x['sequence']))
            assert [int(r['sequence']) for r in path]==list(range(1,len(path)+1))
            ff=[lm[x['physical_leg_id']] for x in path]
            assert ff[0]['origin']==it['origin'] and ff[-1]['destination']==it['destination']
            for f,h in zip(ff,ff[1:]):assert f['destination']==h['origin'] and f['arrival_utc']<=h['departure_utc']
            eq(it['segments'],float(it['trips'])*len(path),'adapter_segments')
            for x in path:
                eq(x['seats'],it['trips'],'adapter_seats');occupancy[x['physical_leg_id']]+=float(x['seats'])
            gross=[r for r in mm if r['itinerary_id']==id and r['entry']=='gross_revenue']
            assert len(gross)==1
            eq(gross[0]['amount_rub'],float(it['trips'])*float(it['fare_once']),'adapter_fare')
        for id,l in lm.items():
            eq(occupancy[id],l['occupied'],'adapter_occupancy');assert occupancy[id]<=float(l['seats'])+1e-7
        fc=[r for r in mm if r['entry']=='flight_variable_cost']
        assert len(fc)==len(lm) and {r['physical_leg_id'] for r in fc}==set(lm)
        for f in fc:eq(f['amount_rub'],lm[f['physical_leg_id']]['flight_variable_cost_rub'],'adapter_perflight')
        eq(sum(float(f['amount_rub']) for f in fc),ss[0]['flight_variable_cost'],'adapter_flight_sum')
        eq(sum(float(m['amount_rub'])*float(m['sign_in_contribution']) for m in mm),ss[0][FIELD],'adapter_money_sum')


def source_holds():
    review=js('context/23_night_run_20261110/source_join_review/handoff.json',commit=SJR,prefix='')
    old_findings=js('context/23_night_run_20261110/source_join_review/findings.json',commit=SJR,prefix='')
    check(review['verdict']=='CHANGES','prior_source_verdict_preserved')
    check(any(r['id']=='SJR-P2-001' and r['impact']['publication_rows']==129 and r['impact']['source_cards']==28 and r['impact']['addendum_mappings']==58 for r in old_findings['findings']),'inherited_exact_source_hold_scope')
    history=[]
    for sha,role,path in [('445a5d523d4b57d8c89b2344e1913de2e5f9dc6b','model_repair','model_repair_review'),('2278b184bbc83c590238c9f461581e3b045a11d0','MR07','budget_review'),('b0b0830b1631b92225d67a8183d9a2792ff007cf','MR05','methods_review')]:
        prior=js('context/23_night_run_20261110/'+path+'/handoff.json',commit=sha,prefix='')
        history.append(dict(role=role,review_commit=sha,verdict=prior['verdict'],old_scope_only=True,extended_by_MR08=False))
    write('prior_acceptance_boundaries.json',history)
    coverage=rows('inputs/primary-001/coverage.csv',grain='directed OD x week, publication incidence, source lineage held')
    primary_receipt=js('inputs/primary-001/receipt.json')
    cov_entry=next(r for r in primary_receipt['files'] if r['path']=='inputs/primary-001/coverage.csv')
    check(cov_entry['source_commit']=='17b4f348f15ea8695688d9435933cb4965568408','primary_receipt_pin')
    check(blob('inputs/primary-001/coverage.csv')==blob(cov_entry['source_path'],commit=cov_entry['source_commit'],prefix='',grain='original publication-incidence table; primary source lineage held'),'primary_coverage_frozen_bytes')
    its=rows(R+'itinerary.csv');pools=rows(R+'market_pool.csv')
    exported=rows(A+'market_publication_context.csv');summary=rows(A+'publication_coverage_summary.csv')
    cov={(r['origin'],r['destination'],r['period_start'],r['period_end']):r for r in coverage}
    check(len(cov)==len(coverage),'publication_unique_key')
    out=[];groups=collections.defaultdict(list)
    for pool,record in zip(pools,exported):
        a,b=pool['market_id'].split('-');candidate=pool['candidate_id'];sc=pool['scenario_id']
        roles={r['transfer'] for r in its if r['candidate_id']==candidate and r['scenario_id']==sc and r['origin']==a and r['destination']==b}
        check(len(roles)==1,'exported_market_role')
        role='TRANSFER_ENDPOINT' if roles=={'True'} else 'LOCAL_ENDPOINT'
        match=cov.get((a,b,pool['period_start'],pool['period_end']))
        eq(pool['D'],record['scenario_D'],'publication_demand_unchanged')
        check(record['observed_endpoint_D']=='' and record['demand_or_capacity_changed']=='False','publication_no_demand_or_capacity_uplift')
        check(record['no_card_means_no_service']=='False' and record['source_acceptance']=='INDEPENDENT_SOURCE_JOIN_REVIEW_PENDING','publication_unknown_not_absence')
        if match:
            check(record['positive_source_cards']==match['positive_source_cards'] and record['source_ids']==match['source_ids'],'publication_incidence_matches_pinned_source')
        out.append(dict(candidate_id=candidate,scenario_id=sc,origin=a,destination=b,role=role,
            has_publication=bool(match and int(match['positive_source_cards'])>0),
            source_lineage='HOLD_INHERITED_SVX_129_ROWS_28_CARDS_58_MAPPINGS_NOT_LIFTED'))
        if sc=='base':groups[candidate,role].append(out[-1])
    check(len(pools)==len(exported)==176,'publication_all_176_markets')
    computed=[]
    for (c,role),rr in sorted(groups.items()):
        computed.append(dict(candidate_id=c,role=role,directed_modeled_markets=len(rr),with_positive_publication=sum(r['has_publication'] for r in rr),acceptance='INCIDENCE_ARITHMETIC_ONLY_PRIMARY_LINEAGE_HOLD'))
    for a,b in zip(computed,summary):
        check(a['candidate_id']==b['candidate_id'] and a['role']==b['role'],'coverage_summary_key')
        eq(a['directed_modeled_markets'],b['directed_modeled_markets'],'coverage_denominator')
        eq(a['with_positive_publication'],b['with_positive_publication'],'coverage_numerator')
    for c,expected in [('H_UFA_4',8),('H_UFA_8',24)]:
        eq(next(r['directed_modeled_markets'] for r in computed if r['candidate_id']==c and r['role']=='TRANSFER_ENDPOINT'),expected,'actual_transfer_denominator')
    write('independent_publication_coverage.csv',computed);write('independent_publication_join.csv',out)
    write('source_hold.json',dict(status='HOLD',inherited_review=SJR,blocking_finding='SJR-P2-001',
        scope='129 inherited SVX publication rows / 28 cards / 58 addendum mappings: source-version lineage',
        incidence_recomputed=True,raw_lineage_reaudited=False,coordinator_derivative_reviewed=False,
        competitive_capacity_accepted=False,observed_market_accepted=False,demand_uplift=0,
        winter_year_inference='HOLD',KUF_SVX_12_clock_conflicts='HOLD',published_schedule_not_performed=True))


if __name__ == '__main__': main()
