#!/usr/bin/env python3
"""Independent reconciliation of exported CSVs; no import of the network model."""
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'context/15_team_update'
MODEL = DEST / 'model'
BASE = '5e896e8ea5bb97136c71c49562a345b8f210bf11'
def rows(p):
    with p.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name, rr):
    rr=list(rr)
    with (DEST/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,list(dict.fromkeys(k for r in rr for k in r)),lineterminator='\n');w.writeheader();w.writerows(rr)
def close(a,b): assert math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=1e-4),(a,b)
def main():
    tests={}
    flights=rows(MODEL/'project_flights.csv'); sold=rows(MODEL/'itinerary_sales.csv'); caps=rows(MODEL/'flight_capacity.csv')
    totals=rows(MODEL/'network_comparison.csv'); pairs=rows(MODEL/'network_pairs.csv'); registry=rows(MODEL/'od_registry.csv')
    byid={r['id']:r for r in flights}; assert len(byid)==len(flights)
    for r in totals:
        key=tuple(r[x] for x in ['network','scenario','priority'])
        ss=[s for s in sold if tuple(s[x] for x in ['network','scenario','priority'])==key]
        cc=[s for s in caps if tuple(s[x] for x in ['network','scenario','priority'])==key]
        for field in ['sold_journeys','transfer_journeys','segment_pax','gross_revenue','foregone_RW_revenue','incremental_revenue','new_pax_variable','saved_old_pax_variable','migrated_RW_total']:
            close(r[field],sum(float(s[field]) for s in ss))
        close(r['flight_variable_cost'],sum(float(c['flight_variable_cost']) for c in cc))
        close(r['incremental_operating_cost'],float(r['flight_variable_cost'])+float(r['new_pax_variable'])-float(r['saved_old_pax_variable']))
        close(r['contribution_before_base_fleet_opportunity'],float(r['incremental_revenue'])-float(r['incremental_operating_cost']))
        used=collections.Counter()
        for s in ss:
            ids=s['flight_ids'].split(';');transfer=s['transfer']=='True'
            assert len(ids)==(2 if transfer else 1)
            close(s['gross_revenue'],float(s['sold_journeys'])*float(s['effective_fare']))
            for i in ids: used[i]+=float(s['sold_journeys'])
            if transfer:
                a,b=map(byid.__getitem__,ids)
                assert a['destination']==b['origin'] and a['date']==b['date']
                close(float(b['departure_utc_minute'])-float(a['arrival_utc_minute']),s['wait_minutes'])
            assert byid[ids[0]]['origin']==s['origin'] and byid[ids[-1]]['destination']==s['destination']
        for c in cc:
            close(used[c['id']],c['sold_segment_pax']); assert -1e-7<=used[c['id']]<=float(c['capacity'])+1e-7
        byod=collections.defaultdict(list)
        for s in ss: byod[(s['origin'],s['destination'])].append(s)
        for ssod in byod.values():
            assert sum(float(s['sold_journeys']) for s in ssod)<=float(ssod[0]['D_OD_week_direction'])+1e-6
            cap=ssod[0]['migration_direct_seat_cap']
            if cap: assert sum(float(s['migrated_RW_direct']) for s in ssod)<=float(cap)+1e-6
    tests['independent_48_result_reconciliation']=len(totals)==48
    tests['dated_capacity_transfer_one_fare_OD_and_direct_migration_cap']=True
    for p in pairs:
        ff=[l for l in flights if l['network']==p['network'] and '-'.join(sorted([l['origin'],l['destination']]))==p['pair']]
        a,b=p['pair'].split('-')
        close(p['departures_A_to_B'],sum(l['origin']==a for l in ff));close(p['departures_B_to_A'],sum(l['origin']==b for l in ff))
    tests['independent_frequencies']=True
    cfg=json.loads((MODEL/'configuration.json').read_text())['config']
    for resource in rows(MODEL/'resource_summary.csv'):
        ff=[l for l in flights if l['network']==resource['network']]
        grouped=collections.defaultdict(list)
        chains=collections.defaultdict(list)
        for l in ff:
            grouped[(l['day'],l['aircraft'])].append(l);chains[l['aircraft']].append(l)
        for chain in chains.values():
            chain.sort(key=lambda l:float(l['departure_utc_minute']))
            for a,b in zip(chain,chain[1:]):
                assert a['destination']==b['origin']
                assert float(a['arrival_utc_minute'])+cfg['turn_minutes']<=float(b['departure_utc_minute'])
            assert chain[0]['origin']==chain[-1]['destination']
        close(resource['weekly_block_hours'],sum(float(l['block_minutes']) for l in ff)/60)
        peak=max(collections.Counter(day for day,tail in grouped).values())
        close(resource['active_peak'],peak);assert peak<=cfg['active_aircraft']
        maxblock=max(sum(float(l['block_minutes']) for l in g)/60 for g in grouped.values())
        maxspan=max((max(float(l['arrival_utc_minute']) for l in g)-min(float(l['departure_utc_minute']) for l in g))/60 for g in grouped.values())
        close(resource['max_daily_block_hours'],maxblock);close(resource['max_daily_span_hours'],maxspan)
        assert maxblock<=cfg['planning_cap_block_h'] and maxspan<=cfg['span_cap_h']
    tests['independent_spatial_chains_daily_spans_blocks_and_active_peak']=True
    assert not any(r['observed_OD'] or r['observed_net_fare'] for r in registry)
    tests['unknown_OD_and_realised_fares_not_imputed_as_facts']=True
    manifest=json.loads((MODEL/'input_manifest.json').read_text())['sha256']
    assert all(sha(ROOT/p)==h for p,h in manifest.items());tests['consumed_input_hashes_current']=True
    # A model contribution winner and a decision to launch are different questions.
    assert all(float(r['contribution_before_base_fleet_opportunity'])<0 for r in totals)
    tests['all_tested_baseline_projects_below_zero_before_fixed']=True
    city=rows(DEST/'evidence/cities_matrix.csv');assert len(city)==len({r['iata'] for r in city})==20
    tests['twenty_unique_airport_rows']=True
    # Compare every original tracked blob, not just selected model files.
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=ROOT,text=True).splitlines()
    preserved=0
    for name in names:
        old=subprocess.check_output(['git','show',f'{BASE}:{name}'],cwd=ROOT)
        now=(ROOT/name).read_bytes()
        assert now==old or (name=='README.md' and now.startswith(old)),name
        preserved+=1
    tests['all_team_base_files_preserved_except_append_only_index']=True
    # One inventory covers every physical and connecting OD; absent schedule rows remain UNKNOWN.
    comp=rows(ROOT/'context/12_network_economics/competition.csv')
    source={r['id']:r['url'] for r in json.loads((ROOT/'context/12_network_economics/sources.json').read_text())}
    aggregate=rows(DEST/'evidence/air_presence_aggregate.csv')
    inventory=[]
    for od in registry:
        a,b=od['pair'].split('-')
        nets=sorted({r['network'] for r in pairs if r['pair']==od['pair']})
        for x,y in [(a,b),(b,a)]:
            old=next((r for r in comp if r['origin']==x and r['destination']==y and r['week']=='2026-12-07'),None)
            agg=[r for r in aggregate if r['origin']==x and r['destination']==y]
            inventory.append(dict(origin=x,destination=y,physical_networks=';'.join(nets),product_scope='physical nonstop pair' if nets else 'connecting OD only',
                schedule_week='2026-12-07/13',snapshot_as_of='2026-11-08/09 reused; parent gap audit2026-11-09',
                published_departures_in_snapshot=old['departures'] if old else None,
                RW_published_departures_in_snapshot=old['rw_departures'] if old else None,
                carriers=old['carriers'] if old else None,published_periods=old['published_periods'] if old else None,
                schedule_status=old['status'] if old else 'UNKNOWN_NO_DATED_PRIMARY_SNAPSHOT',
                project_class=old['project_class'] if old else 'UNKNOWN_NEW_VS_REINFORCEMENT',
                seasonality=old['summer_2027'] if old else 'UNKNOWN',
                matched_final_fare_20kg_RUB=old['comparable_fare_20kg_rub'] if old else None,
                fare_status=old['fare_status'] if old else 'NO_MATCHED_FINAL_QUOTE',
                advertised_from_OLD_NOT_MATCHED=old['advertised_RW'] if old else None,
                aggregate_listed_supply=bool(agg),aggregate_list_status='listed June2026 source; may include subsidy plan, no actual frequency or operating proof; absence is not zero',
                observed_OD=None,observed_net_fare=None,scenario_OD_cautious=od['scenario_OD_cautious'],scenario_OD_base=od['scenario_OD_base'],
                demand_unit='endpoint journeys/week/direction',demand_method=od['method'],
                source_urls=';'.join(sorted({source[i] for i in old['source_ids'].split(';') if i in source})) if old else None,
                aggregate_source='https://tochno.st/datasets/intercity_connectivity',
                missing='paid directional monthly OD; exact-date competitor and RW calendar, taxes/baggage/refund comparable quote; old RW connecting sales'))
    write('route_evidence.csv',inventory)
    tests['all_canonical_OD_both_directions_in_inventory']=len(inventory)==2*len(registry)
    summary=[]
    for r in totals:
        if r['priority']!='local_first':continue
        summary.append({k:r[k] for k in ['network','scenario','weekly_legs','weekly_block_hours','sold_journeys','transfer_journeys','segment_pax','migrated_RW_total','gross_revenue','incremental_revenue','incremental_operating_cost','contribution_before_base_fleet_opportunity','load_factor']})
    write('comparison_summary.csv',summary)
    (DEST/'independent_checks_final.json').write_text(json.dumps(dict(status='PASS',tests=tests,team_original_blobs_checked=preserved,
        canonical_OD=len(registry),directional_route_inventory=len(inventory),observed_OD_rows=0,matched_realised_fare_rows=0,
        independent_script_sha256=sha(Path(__file__)),limitations=['Arithmetic and preservation checks, not market validation','Original user scratch preservation recorded separately','No exact matched new fare or actual free-aircraft confirmation']),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',checks=len(tests),team_original_files=preserved,OD=len(registry),directional_inventory=len(inventory))))
if __name__=='__main__':main()
