#!/usr/bin/env python3
"""Small, independent arithmetic on pinned exports. No author pipeline claim."""
import ast
import collections
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / 'inputs/set001'
OUT = ROOT / 'analysis/set001'


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def save(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    if name.endswith('.json'):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    else:
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, list(dict.fromkeys(k for r in data for k in r)))
            writer.writeheader()
            writer.writerows(data)


def main():
    checks = []
    manifest = json.loads((ROOT / 'source_manifest.json').read_text())
    for entry in manifest['files']:
        assert hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest() == entry['sha256']
    checks.append(dict(check='pinned_blob_hashes', status='PASS', n=len(manifest['files'])))
    nastya = INPUT/'nastya_2f03'
    assumptions = {r['parameter']:{s:float(r[s]) for s in ['base','cautious']}
                   for r in rows(nastya/'data/assumptions/network.csv')}
    routes = rows(nastya/'data/processed/network_routes.csv')
    demand = {tuple(sorted((r['a'],r['b']))):r for r in rows(nastya/'data/processed/demand_pairs.csv')}
    # Execute ONLY these three pure author functions, unchanged AST.
    tree = ast.parse((nastya/'src/network_model.py').read_text())
    names = {'capture','leg_share','fare'}
    body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    namespace = {'math':math}
    exec(compile(ast.Module(body=body,type_ignores=[]), 'pinned/network_model.py:pure_functions', 'exec'), namespace)
    shared = []
    counts = []
    for scenario in ['base','cautious']:
        A = {k:v[scenario] for k,v in assumptions.items()}
        selected = [r for r in routes if r['scenario']==scenario and r['variant'].startswith('Прямые')]
        groups = collections.defaultdict(list)
        for r in selected:
            groups[tuple(sorted((r['from'],r['to'])))].append(r)
        counts.append(dict(model_id='nastya_2f03',scenario=scenario,author_program_count=len({r['variant'] for r in selected}),
                           physical_pair_count=len(groups),leg_rows=len(selected),
                           weekly_departures=sum(2*int(r['freq_week_each_way']) for r in selected)))
        for pair, rs in groups.items():
            if len(rs)<2:
                continue
            D = demand.get(pair)
            assert D is not None, pair
            annual = float(D['observed'] if scenario=='base' and D['observed'] and D['observed_coverage']!='airline_group'
                           else D['pax_base' if scenario=='base' else 'pax_cautious'])
            W = A['weeks_per_year']
            freqs = [int(r['freq_week_each_way']) for r in rs]
            leg = dict(dem=annual/(2*W),km=float(rs[0]['km']),competitive=rs[0]['direct_now']=='True')
            separate = sum(min(leg['dem']*namespace['leg_share'](leg,f,A),f*A['seats']*A['lf_max'])*2*W for f in freqs)
            unified = min(leg['dem']*namespace['leg_share'](leg,sum(freqs),A),sum(freqs)*A['seats']*A['lf_max'])*2*W
            exported = sum(float(r['pax_year_segments']) for r in rs)
            assert abs(separate-exported)<=len(rs)*.5+1e-6
            shared.append(dict(model_id='nastya_2f03',scenario=scenario,pair='-'.join(pair),program_count=len(rs),
                direction_scope='BOTH_DIRECTIONS_SYMMETRIC_ASSUMPTION',weeks=W,
                author_market_input_annual=annual,source_unit='SEGMENT_SCALE_USED_AS_SCENARIO_OD',
                source_coverage=D['observed_coverage'] or 'gravity_proxy',
                frequencies_each_way='+'.join(map(str,freqs)),author_exported_pax=exported,
                author_formula_recomputed_pax=separate,pooled_frequency_counterfactual_pax=unified,
                difference_pax=unified-separate,actual_total_market_cap_breached=exported>annual,
                status='AGENT_PROPOSAL_FIXED_SELECTION_NOT_CORRECTED_REPLAY',
                limitation='No dated departures; no reselection; no OD observation; aggregation law is a scenario'))
    save('shared_pair_examples.csv',shared)
    save('route_counts.csv',counts)
    checks.append(dict(check='nastya_duplicate_pair_export_arithmetic',status='PASS',n=len(shared)))
    hub_balances=[]
    for r in rows(nastya/'data/processed/network_summary.csv'):
        delta=float(r['segments_year'])-float(r['od_trips_year'])-float(r['transfer_od_year'])
        assert abs(delta)<=1
        hub_balances.append(dict(scenario=r['scenario'],variant=r['variant'],
                                segment_pax=r['segments_year'],journeys=r['od_trips_year'],
                                transfer_journeys=r['transfer_od_year'],rounding_residual=delta))
    save('nastya_export_balances.csv',hub_balances)
    checks.append(dict(check='nastya_journey_segment_identity_export_rounding',status='PASS',n=len(hub_balances)))
    tsiri=INPUT/'tsiri_93fa/context'
    comparison=rows(tsiri/'21_team_proposals/comparison.csv')
    sales=rows(tsiri/'17_aircraft_route_review/model/sales.csv')
    capacities=rows(tsiri/'17_aircraft_route_review/model/capacity.csv')
    flights=rows(tsiri/'17_aircraft_route_review/model/flights.csv')
    ledger=[]
    examples=[]
    for result in comparison:
        profile,network,scenario = result['source_profile'],result['source_network'],result['scenario']
        ss=[s for s in sales if (s['profile'],s['network'],s['scenario'])==(profile,network,scenario)]
        cc=[c for c in capacities if (c['profile'],c['network'],c['scenario'])==(profile,network,scenario)]
        ff={f['id']:f for f in flights if (f['profile'],f['network'])==(profile,network)}
        assert ss and cc and ff
        sums={k:sum(float(s[k]) for s in ss) for k in ['sold_journeys','transfer_journeys','segment_pax',
             'gross_revenue','foregone_RW_revenue','incremental_revenue','new_pax_variable','saved_old_pax_variable']}
        for k,v in sums.items():
            assert math.isclose(v,float(result[k]),abs_tol=1e-5), (result['network'],scenario,k)
        used=collections.Counter()
        markets=collections.Counter()
        for s in ss:
            ids=s['flight_ids'].split(';')
            q=float(s['sold_journeys'])
            assert math.isclose(float(s['gross_revenue']),q*float(s['fare_once']),abs_tol=1e-6)
            assert math.isclose(float(s['segment_pax']),q*len(ids),abs_tol=1e-6)
            for i in ids:
                assert i in ff
                used[i]+=q
            markets[(s['origin'],s['destination'])]+=q
        for s in ss:
            assert markets[(s['origin'],s['destination'])]<=float(s['D'])+1e-6
        for c in cc:
            assert math.isclose(used[c['flight_id']],float(c['occupied']),abs_tol=1e-6)
            assert used[c['flight_id']]<=float(c['capacity_scenario'])+1e-6
        cost=float(result['flight_variable_cost'])+sums['new_pax_variable']-sums['saved_old_pax_variable']
        contribution=sums['gross_revenue']-sums['foregone_RW_revenue']-cost
        assert math.isclose(contribution,float(result['contribution_before_base_fleet_opportunity']),abs_tol=1e-5)
        ledger.append(dict(network=result['network'],scenario=scenario,period_start='2026-12-07',period_end='2026-12-13',
            **sums,flight_variable_cost=float(result['flight_variable_cost']),incremental_operating_cost=cost,
            contribution_before_unknown_fixed=contribution,full_budget_profit=None,
            full_budget_status='UNKNOWN_BASE_FLEET_STARTUP_WORKING_CAPITAL_OPPORTUNITY',
            weekly_block_hours=result['weekly_block_hours'],active_allocated=result['active_allocated'],reserve=1,
            value_status='AUTHOR_EXPORTED_ARITHMETIC_CHECKED_NOT_FULL_PIPELINE_REPLAY'))
        if result['network']=='H_UFA_8' and scenario=='base':
            s=next(s for s in ss if s['transfer']=='True' and float(s['sold_journeys'])>0)
            examples.append(dict(**s,legs=[ff[i] for i in s['flight_ids'].split(';')]))
    save('tsiri_money_reconciliation.csv',ledger)
    save('itinerary_example.json',examples)
    checks.append(dict(check='tsiri_8_exports_sales_legs_seats_market_and_money',status='PASS',n=len(comparison)))
    hp=INPUT/'hypotheses_6ed8/context/16_agent_research/hypotheses/experiment_v1'
    table=rows(hp/'cost_resource/6cf441ef38e2c6c5/conditional_thresholds_with_product_keys.csv')
    example=next(r for r in table if r['candidate']=='C01' and float(r['residual_funding_gap_rub'])==1e6
        and float(r['net_fare_rub_per_oneway_journey'])==8000 and float(r['variable_cost_rub_per_oneway_journey'])==500)
    q=math.ceil(1e6/(2*(8000-500)))
    assert q==int(example['required_paid_journeys_each_direction'])==67
    assert int(example['physical_boardings'])==q*4==268
    assert 2*(q-1)*(8000-500)<1e6<=2*q*(8000-500)
    save('product_threshold_example.json',example)
    checks.append(dict(check='C01_integer_threshold_and_leg_multiplier',status='PASS',n=1))
    save('checks.json',dict(status='PASS_SCOPED',checks=checks,
        not_run=['full author code/data pipelines','raw-to-derived extraction','independent review',
                 'common dated network optimisation','empirical market validation','full strategy budget'],
        acceptance_scope=['RAW_HASH_VERIFIED','EXTRACTION_CHECKED_selected_exports','JOIN_CHECKED_selected_exports','CONSERVATION_PASS_selected_tsiri_exports']))
    print(json.dumps({'status':'PASS_SCOPED','checks':len(checks),'shared_pairs':len(shared),'tsiri_results':len(comparison)}))


if __name__=='__main__':
    main()
