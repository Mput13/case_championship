#!/usr/bin/env python3
"""Independent accounting/calendar identities and immutable-input acceptance checks."""
import csv
import hashlib
import json
import math
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
REPO=BASE.parents[2]
OUT=HERE/'outputs'
checks=[]


def read(p):
    with p.open() as f:return list(csv.DictReader(f))


def ok(name,condition):
    checks.append(dict(check=name,passed=bool(condition)))
    assert condition,name


def close(a,b):
    return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=.0001)


def main():
    pins=json.loads((BASE/'input_manifest.json').read_text())
    ok('16 original input hashes',len(pins)==16 and all(hashlib.sha256((BASE/r['local']).read_bytes()).hexdigest()==r['sha256'] for r in pins))
    public=json.loads((BASE/'public_sources_manifest.json').read_text())
    ok('nine captured primary source hashes',len(public)==9 and all(r['status']=='HTTP_READ_OK' and hashlib.sha256((BASE/r['local']).read_bytes()).hexdigest()==r['sha256'] for r in public))
    extra=json.loads((HERE/'additional_input_manifest.json').read_text())['inputs']
    ok('13 evidence06cb hashes',len(extra)==13 and all(hashlib.sha256((BASE/r['local']).read_bytes()).hexdigest()==r['sha256'] for r in extra))
    final_extra=json.loads((HERE/'final_evidence_input_manifest.json').read_text())['inputs']
    ok('17 final evidence38f hashes',len(final_extra)==17 and all(hashlib.sha256((BASE/r['local']).read_bytes()).hexdigest()==r['sha256'] for r in final_extra))
    frozen='941d9ebfe97c86baa210da2c56bb1f94cbe298b0'
    prefix=str(BASE.relative_to(REPO))
    files=subprocess.check_output(['git','ls-tree','-r','--name-only',frozen,'--',prefix],cwd=REPO,text=True).splitlines()
    ok('all25 first-slice files unchanged at original paths',len(files)==25 and all((REPO/f).read_bytes()==subprocess.check_output(['git','show',frozen+':'+f],cwd=REPO) for f in files))
    params=read(BASE/'inputs/owner4a976/data/assumptions/network.csv')
    A={s:{r['parameter']:float(r[s]) for r in params} for s in ['base','cautious']}
    # Independent exact cost check for four added directional flights totalling9 block-hours.
    for s in ['base','cautious']:
        a=A[s]
        expected=((a['fuel_t_per_hour']*9+a['fuel_t_per_cycle']*4)*a['fuel_rub_per_t']
                  +(a['mro_rub_per_hour']+a['crew_rub_per_hour']+a['navigation_rub_per_hour'])*9
                  +4*(a['ground_rub_per_flight']+a['deicing_rub_per_flight']))
        rr=[r for r in read(OUT/'C07_extension.csv') if r['scenario']==s]
        ok('C07 independent 9h/4cycle cost '+s,all(close(r['extra_fixed_flight_cost_rub_week'],expected) for r in rr))
    for r in read(OUT/'C07_extension.csv'):
        ok('C07 signed incremental budget '+r['scenario']+r['turn_minutes'],
           close(float(r['delta_ticket_revenue_rub_week'])-float(r['delta_pax_cost_rub_week'])-float(r['extra_fixed_flight_cost_rub_week']),r['delta_contribution_rub_week']))
    for r in read(OUT/'C01_synchronization.csv'):
        cap=2*float(r['capacity_per_leg_one_direction'])
        t=float(r['new_through_journeys_week'])
        ok('C01 physical shared seats and one fare '+r['scenario']+r['local_loss_fraction_south'],
           float(r['local_north_after_week'])+t<=cap+1e-7 and float(r['local_south_after_week'])+t<=cap+1e-7
           and close(float(r['segments_week']),float(r['total_journeys_week'])+t)
           and close(float(r['ticket_revenue_sync_rub_week'])-float(r['fixed_flight_cost_rub_week'])-float(r['pax_cost_sync_rub_week']),r['contribution_sync_rub_week'])
           and close(float(r['contribution_sync_rub_week'])-float(r['contribution_unsync_rub_week']),r['delta_contribution_rub_week']))
    timed=read(OUT/'C33_retiming.csv')
    for r in timed:
        ok('C33 signed budget and segment/journey difference '+r['scenario']+r['occupied_state']+r['local_loss_fraction_trunk'],
           close(float(r['ticket_revenue_after_rub_week'])-float(r['ticket_revenue_before_rub_week'])-float(r['delta_pax_cost_rub_week']),r['delta_contribution_rub_week'])
           and close(float(r['segment_delta_week'])-float(r['net_journey_delta_week']),r['new_through_journeys_week']))
    ok('filled physical seats counterexample prevents free-growth claim',all(float(r['delta_contribution_rub_week'])<=1e-6 for r in timed if r['occupied_state']=='all_physical_seats_sold'))
    flights=read(OUT/'dated_flights.csv')
    ok('146 labelled flights',len(flights)==146 and all(r['schedule_status'] for r in flights))
    seq=defaultdict(list)
    for r in flights:seq[(r['network'],r['variant'],r['tail_scenario'])].append(r)
    for key,rows in seq.items():
        rows.sort(key=lambda r:r['departure_utc'])
        ok('tail continuity and nonoverlap '+str(key),all(
            datetime.fromisoformat(a['arrival_utc'])<=datetime.fromisoformat(b['departure_utc']) and a['destination']==b['origin']
            for a,b in zip(rows,rows[1:])))
    old=[r for r in flights if r['network']=='C33' and r['variant']=='KEEP']
    new=[r for r in flights if r['network']=='C33' and r['variant']=='retime']
    fields=['flight_id','flight_number','origin','destination','service_date','block_minutes']
    ok('C33 same eight flight IDs dates pairs and blocks',len(old)==len(new)==8 and sorted(tuple(r[k] for k in fields) for r in old)==sorted(tuple(r[k] for k in fields) for r in new))
    waits=read(OUT/'C33_tail_waits.csv')
    ok('C33 OMS wait50->1815, same415block/2370span/510nextground',all(close(r['total_block_minutes'],415) and close(r['rotation_elapsed_minutes'],2370) and close(r['next_turn_minutes'],510) and close(r['OMS_wait_minutes'],50 if r['variant']=='KEEP' else 1815) for r in waits))
    con=read(OUT/'dated_connections.csv')
    ok('90minute MCT counterexample blocks both connection products',all(r['passes']=='False' for r in con if r['min_connection_minutes']=='90'))
    ok('60minute MCT diagnostic passes sync/retime and fails baseline',all((r['passes']=='True')==(r['variant'] in ['sync','retime']) for r in con if r['min_connection_minutes']=='60'))
    nxt=[r for r in read(OUT/'C07_next_assignment.csv') if r['applies_real_example']=='True']
    ok('real Wed07:25 opportunity slack10/-50/-110',[(r['variant'],float(r['slack_minutes'])) for r in nxt]==[('turn30',10),('turn45',-50),('turn60',-110)])
    next33=read(OUT/'C33_next_assignment.csv')
    ok('C33 middle-window assignment opportunity retained as cost boundary',[(r['variant'],float(r['slack_minutes'])) for r in next33]==[('KEEP',305),('retime',-900)])
    resources=read(OUT/'fixed_daily_resources.csv')
    ok('diagnostic tail-day caps10bh/14h respected',all(float(r['block_minutes'])<=600 and float(r['elapsed_minutes'])<=840 and r['location_start']==r['location_end'] for r in resources))
    # Independent geometric screen of every proposed fixed-program physical leg.
    nodes={r['iata']:r for r in read(BASE/'inputs/owner4a976/data/processed/catchments.csv')}
    south={r['region'] for r in read(BASE/'inputs/owner4a976/data/assumptions/south_west_regions.csv')}
    for r in read(OUT/'fixed_routes.csv'):
        if r['scenario']!='base':continue
        aa,bb=nodes[r['origin']],nodes[r['destination']]
        lat1,lon1,lat2,lon2=[math.radians(float(v)) for v in [aa['latitude_deg'],aa['longitude_deg'],bb['latitude_deg'],bb['longitude_deg']]]
        km=2*6371*math.asin(math.sqrt(math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2))
        limit=2150 if {aa['region'],bb['region']}&south else 2300
        ok('pinned SSJ scenario geometric limit '+r['network']+r['destination'],km<=limit)
    deltas=read(OUT/'route_deltas.csv')
    ok('integration keys scenario/network/route/date explicit',all(r['scenario'] in ['base','cautious'] and r['network'] and r['route'] and r['date'] for r in deltas))
    # Reconstruct bank contribution from OD sales with two consumed seats, not two fares.
    sales=read(OUT/'bank_upper_bound_sales.csv');fixed=read(OUT/'fixed_programs.csv')
    fares=read(OUT/'demand_fare_inputs.csv')
    for r in read(OUT/'bank_upper_bound.csv'):
        s,net=r['scenario'],r['network'];a=A[s]
        gross=pax_cost=0.;loads=defaultdict(float)
        hub=r['hub']
        for x in [x for x in sales if x['network']==net and x['scenario']==s]:
            d=next(z for z in fares if z['scenario']==s and z['origin']==x['origin'] and z['destination']==x['destination'] and z['frequency_each_direction']=='2')
            q=float(x['journeys_week']);transfer=x['product_type']=='transfer'
            gross+=q*float(d['net_fare_rub'])*(a['transfer_fare_factor'] if transfer else 1)
            pax_cost+=float(x['segments_week'])*a['pax_cost_rub']
            if transfer:loads[x['origin']]+=q;loads[x['destination']]+=q
            else:loads[x['destination']]+=q
        f=next(x for x in fixed if x['network']==net and x['scenario']==s)
        fixedcost=float(f['variable_cost_rub_week'])-float(f['local_journeys_week'])*a['pax_cost_rub']
        ok('bank one-fare/shared-capacity budget '+s+net,
           close(gross-pax_cost-fixedcost,r['ideal_bank_contribution_rub_week'])
           and all(v<=4*100*a['lf_max']+1e-6 for v in loads.values()) and r['missing_od_pair_count']=='0')
    add=json.loads((HERE/'evidence_addendum.json').read_text())
    ok('subsidy rows not interpreted as frequency and supportedPnL not invented',add['supplied_scope']['service_rows_are_frequencies'] is False and add['supported_case'].startswith('NOT_CALCULATED'))
    for r in read(OUT/'subsidy_payment_caps_only.csv'):
        ok('pure per-flight cap arithmetic '+r['route'],close(float(r['cap_rub_per_oneway_completed_flight'])*float(r['hypothetical_completed_eligible_flights']),r['arithmetic_payment_ceiling_rub']) and r['supported_PnL'].startswith('NOT_CALCULATED'))
    final=json.loads((HERE/'final_evidence_addendum.json').read_text())
    ok('final215 unique departures,144 duplicates,12 conflicts retained',final['counts']['unique_instances']==215 and final['counts']['duplicates_collapsed']==144 and final['counts']['conflicting_instances']==12)
    ok('C33 exact8 published baseline instances with2 conflicts retained',final['C33_current_baseline_matched_flights']==8 and final['C33_selected_conflicting_instances']==2)
    result=dict(status='PASS',scope='personal offline arithmetic/provenance/calendar checks, not independent review or market/engineering acceptance',
                checks_passed=len(checks),checks=checks,not_run=['real bookings/flights','UIQA','full evidence parser review','supported compliant fare/net-yield calculation','future annual/company N(t) model'])
    (HERE/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('PASS',len(checks),'accounting/calendar/provenance checks')


if __name__=='__main__':
    main()
