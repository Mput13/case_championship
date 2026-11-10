#!/usr/bin/env python3
"""MR11 independent stdlib oracle. Every owner input is an exact git object.

No owner algorithm is used for the financial oracle. Owner code is compiled
only in probes.py for adversarial and deterministic-replay comparisons.
"""
import collections
import csv
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import subprocess
from datetime import datetime, timedelta

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
PREFIX = 'context/23_night_run_20261110/methods/'
SUBJECT = 'f7a034dc91917cc69c5f8b3a729c3d1c6dfeb5b9'
COMMON = 'abb1c76254d2d4e3cf9edd5c345b9cdb224f6abe'
PRIOR = 'c24bbd36356f46763eed5a1654573b6de31adc6b'
TIMEFIX = '87ee52de15c2bdf396d9c06ba600fd413d5ab4a8'
ROOT = '77343ca9dccc14d60c51d4559485646219ecd1cd'
SRC = 'inputs/set001/tsiri_93fa/context/'
MONEY = ['gross_revenue', 'foregone_RW_revenue', 'new_pax_variable', 'saved_old_pax_variable']
QUANT = ['sold_journeys', 'transfer_journeys', 'segment_pax', 'migrated_RW_total',
         'migrated_RW_direct', 'migrated_RW_unverified_connecting']
TOTAL = MONEY + QUANT + ['flight_variable_cost', 'incremental_revenue',
         'contribution_before_base_fleet_opportunity', 'load_factor', 'net_new_RW_journeys_scenario']
RECEIPTS = {}
CHECKS = collections.Counter()


def grain_for(path):
    if not path.endswith('.csv'):return 'scoped document, code, contract, manifest or historical review receipt'
    if 'cash' in path:return 'profile/network/author_scenario/policy/relative_day/event; incremental net RUB and balance-sheet deltas'
    if 'demand_mapping' in path:return 'network/scenario/undirected source pair; annual proxy and scenario weekly journeys per direction (annual/104)'
    if 'flights.csv' in path:return 'profile/network/physical flight id; dated directed leg, absolute UTC minutes from period epoch, seats'
    if 'capacity.csv' in path:return 'profile/network/scenario/physical flight id; physical seats, occupied seat-segments, RUB variable flight cost'
    if '/model/sales.csv' in path:return 'profile/network/scenario/ordered itinerary flight_ids; directed final OD journeys and one net RUB through fare'
    if 'itinerary' in path or 'journeys' in path:return 'candidate or portfolio/scenario/recipe or capture law/ordered itinerary flight_ids; endpoint journeys, seat-segments, one-fare net RUB'
    if 'demand_pairs' in path:return 'unordered source airport pair; annual directionalization proxy inputs and source coverage, not observed winter OD'
    if 'calendar' in path:return 'candidate/scenario/namespaced working tail; leg count and minimum model turnaround minutes'
    if 'physical_leg' in path or 'timestamp' in path:return 'profile/network/scenario/policy/physical flight id; source time projection or operation status, hash transfer only here'
    if 'rotation_conflicts' in path:return 'profile/network/scenario/policy/tail/adjacent flight ids; inherited corrected resource conflict, hash transfer only here'
    if 'market' in path:return 'candidate or portfolio/scenario/capture law/directed origin-destination; one scenario market and old-seat budget'
    if 'comparison.csv' in path:return 'context21 candidate/scenario with source_profile/source_network; weekly scenario journeys and net RUB contribution before fixed costs'
    if 'threshold' in path:return 'candidate/scenario/cancellation policy; inverse scenario RUB per affected endpoint journey, unknown fixed burden retained'
    if 'acceptance_matrix' in path:return 'artifact/exact input commit/review commit; bounded acceptance and explicit excluded scope'
    if 'summary' in path or 'overlay' in path:return 'candidate or portfolio/scenario/recipe or capture law/policy; weekly endpoint journeys and conditional net RUB, NULL retained'
    return 'original keyed row-level check or diagnostic; no empirical acceptance upgrade'


def raw(path, sha=SUBJECT, full=False, grain=None):
    path = path if full else PREFIX + path
    key = sha + ':' + path
    b = subprocess.check_output(['git', 'show', key], cwd=REPO)
    RECEIPTS[key] = dict(commit=sha, path=path, bytes=len(b), sha256=hashlib.sha256(b).hexdigest(),
                         git_blob_sha1=hashlib.sha1(b'blob ' + str(len(b)).encode()+b'\0'+b).hexdigest(),
                         grain=grain or grain_for(path))
    return b


def rows(path, sha=SUBJECT):
    return list(csv.DictReader(io.StringIO(raw(path, sha).decode('utf-8-sig'))))


def obj(path, sha=SUBJECT):
    return json.loads(raw(path, sha))


def save(name, data):
    if name.endswith('.json'):
        (OUT/name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    else:
        with (OUT/name).open('w', newline='') as f:
            w = csv.DictWriter(f, list(dict.fromkeys(k for r in data for k in r)))
            w.writeheader(); w.writerows(data)


def near(a, b, label, tol=1e-6):
    assert math.isfinite(float(a)) and math.isfinite(float(b)), (label, a, b)
    assert abs(float(a)-float(b)) <= tol, (label, a, b, float(a)-float(b))
    CHECKS[label.split(':')[0]] += 1


def keyed(rs, fields):
    result = {tuple(r[f] for f in fields):r for r in rs}
    assert len(result) == len(rs), ('duplicate keys', fields)
    return result


def components(f, p):
    h = float(f['block_minutes']) / 60
    fuel = h*p['fuel_t_per_hour'] + p['fuel_t_per_cycle']
    return dict(fuel_product=fuel*p['fuel_rub_per_t'], fuel_uplift=fuel*p['fuel_uplift_rub_per_t'],
                mro=h*p['mro_rub_per_hour'], crew=h*p['crew_rub_per_hour'], navigation=h*p['navigation_rub_per_hour'],
                airport_turn=(49.45*(553+499)+19300+8100+16668)*p['airport_factor'],
                deicing=p['deicing_probability']*p['deicing_operation_rub'])


def selected_flights(allflights, r):
    ff = [f for f in allflights if (f['profile'], f['network']) == (r['source_profile'], r['source_network'])]
    keyed(ff, ['id'])
    return ff


def touched(ff, defs):
    start = datetime.fromisoformat(defs['episode']['start_utc'])
    end = datetime.fromisoformat(defs['episode']['end_utc_exclusive'])
    epoch = datetime.fromisoformat(defs['period_start']+'T00:00:00+00:00')
    airport = defs['episode']['airport']
    return {f['id'] for f in ff if
            (f['origin'] == airport and start <= epoch+timedelta(minutes=float(f['departure_utc_minute'])) < end)
            or (f['destination'] == airport and start <= epoch+timedelta(minutes=float(f['arrival_utc_minute'])) < end)}


def cancellation(ss, ff, p, fractions, defs):
    ids = {f['id'] for f in ff}
    keyed(ss, ['flight_ids'])
    assert {i for s in ss for i in s['flight_ids'].split(';')} == ids
    hit = touched(ff, defs)
    affected = [s for s in ss if hit.intersection(s['flight_ids'].split(';'))]
    q = sum(float(s['sold_journeys']) for s in affected)
    lost = sum(float(s['sold_journeys'])*float(s['fare_once']) for s in affected)
    segs = sum(float(s['sold_journeys'])*len(s['flight_ids'].split(';')) for s in affected)
    pax = sum(float(s['sold_journeys'])*len(s['flight_ids'].split(';'))*p['pax_cost'] for s in affected)
    cost = collections.Counter()
    for f in ff:
        if f['id'] in hit:
            for k, v in components(f, p).items(): cost[k] += v*fractions[k]
    cost['new_pax_variable'] = pax*fractions['new_pax_variable']
    for s in ss:
        near(float(s['sold_journeys'])*float(s['fare_once']), s['gross_revenue'], 'fare_once:source')
        near(float(s['sold_journeys'])*len(s['flight_ids'].split(';'))*p['pax_cost'], s['new_pax_variable'], 'pax_segments:source')
    saved = sum(cost.values())
    return dict(cancelled_legs=len(hit), affected_journeys=q, unserved_segments=segs,
                lost_fare_once=lost, avoidable_costs=saved, delta=saved-lost,
                affected_rows=len(affected), double_touched_rows=sum(len(hit.intersection(s['flight_ids'].split(';'))) == 2 for s in affected)), affected, cost


def run_cancellation(flights, params, results, defs):
    # Frozen v3 C/N is read from COMMON, never substituted with a new run.
    sales = rows('runs/common_demand_v1/itinerary_at_unit_scale.csv', COMMON)
    baseline = keyed(rows('runs/common_demand_v1/summary.csv', COMMON), ['network','scenario','recipe','multiplier'])
    published = keyed(rows('runs/kover_demand_v1/summary.csv'), ['candidate','scenario','recipe','policy'])
    interaction = []; incidences = []
    for n, sc, recipe in itertools.product(['H_UFA_4','H_UFA_8'], ['base','cautious'], ['C','N']):
        r = baseline[n,sc,recipe,'1']; ff = selected_flights(flights, r)
        ss = [s for s in sales if (s['network'],s['scenario'],s['recipe'],s['multiplier']) == (n,sc,recipe,'1')]
        for policy in [x for x in defs['scenarios'] if x['action']=='cancel']:
            v, aff, cost = cancellation(ss, ff, params[sc], defs['avoidability_profiles'][policy['avoidability']], defs)
            ledger = {k:sum(float(s[k]) for s in ss) for k in MONEY}
            full_flight_cost = sum(sum(components(f,params[sc]).values()) for f in ff)
            independent_baseline = ledger['gross_revenue']-ledger['foregone_RW_revenue']-full_flight_cost-ledger['new_pax_variable']+ledger['saved_old_pax_variable']
            near(independent_baseline,r['contribution_before_base_fleet_opportunity'],'CN16:baseline_from_primitives')
            final = float(r['contribution_before_base_fleet_opportunity']) + v['delta']
            primitive_final = ledger['gross_revenue']-v['lost_fare_once']-ledger['foregone_RW_revenue']-(full_flight_cost-v['avoidable_costs']+cost['new_pax_variable'])-(ledger['new_pax_variable']-cost['new_pax_variable'])+ledger['saved_old_pax_variable']
            near(final,primitive_final,'CN16:final_without_restoring_or_rededucting_migration')
            remaining = float(r['sold_journeys']) - v['affected_journeys']
            x = published[n,sc,recipe,policy['id']]
            compare = dict(cancelled_physical_legs=v['cancelled_legs'], unserved_journeys=v['affected_journeys'],
                           lost_fare_once=v['lost_fare_once'], avoidable_costs=v['avoidable_costs'],
                           baseline_contribution=r['contribution_before_base_fleet_opportunity'], delta_before_unknown=v['delta'],
                           contribution_after_before_unknown=final, remaining_journeys=remaining)
            for k,val in compare.items(): near(val, x[k], 'CN16:'+k)
            assert x['full_budget']==x['actual_cash_peak']=='' and final < 0
            interaction.append(dict(candidate=n, scenario=sc, recipe=recipe, policy=policy['id'], **v,
                                    contribution_after=final, remaining_journeys=remaining, full_budget=None, actual_cash=None))
            if policy['id']=='cancel_pretravel_no_protection':
                for a in aff:
                    incidences.append(dict(candidate=n,scenario=sc,recipe=recipe,flight_ids=a['flight_ids'],
                        affected_leg_count=len(touched(ff, defs).intersection(a['flight_ids'].split(';'))),
                        journeys=float(a['sold_journeys']),fare_once=float(a['fare_once']),lost_fare_once=float(a['gross_revenue'])))
    assert len(interaction)==16
    save('independent_cancellation16.csv', interaction); save('independent_affected_itinerary.csv', incidences)
    differences=[]
    for n,sc,pol in itertools.product(['H_UFA_4','H_UFA_8'],['base','cautious'],[p['id'] for p in defs['scenarios'] if p['action']=='cancel']):
        c=next(x for x in interaction if (x['candidate'],x['scenario'],x['recipe'],x['policy'])==(n,sc,'C',pol))
        new=next(x for x in interaction if (x['candidate'],x['scenario'],x['recipe'],x['policy'])==(n,sc,'N',pol))
        differences.append(dict(candidate=n,scenario=sc,policy=pol,C_delta=c['delta'],N_delta=new['delta'],
                                error_if_C_delta_transplanted=c['delta']-new['delta']))
    for n,cv,nv in [('H_UFA_4',255219.47,-605120.27),('H_UFA_8',854454.45,-998495.53)]:
        x=next(x for x in differences if (x['candidate'],x['scenario'],x['policy'])==(n,'base','cancel_pretravel_no_protection'))
        near(x['C_delta'],cv,'rounded_anchor:C',.005); near(x['N_delta'],nv,'rounded_anchor:N',.005)
    save('independent_CN_deltas.csv', differences)
    # Annual /104 remains a symmetric weekly directional stress, not winter OD.
    for d in rows('runs/common_demand_v1/demand_mapping.csv', COMMON):
        near(float(d['N_annual_proxy'])/104,d['N_week_direction_stress'],'annual_proxy:104')
        assert d['status']=='SOURCE_RECIPE_SCALE_NOT_OBSERVED_ENDPOINT_OD'
    return interaction


def run_adapter(flights, sales, params, results, defs):
    receipt=obj('inputs/cost-timebase-002/receipt.json')
    # Verify imported bytes against the exact parent correction, not its raw or algorithm.
    for f in receipt['files']:
        imported=raw(f['path'])
        parent=raw(f['source_path'],TIMEFIX,True)
        assert imported==parent and hashlib.sha256(imported).hexdigest()==f['sha256']
    fixed=keyed(rows('inputs/cost-timebase-002/scenario_summary.csv'),['profile','network','author_scenario','scenario_id'])
    original=keyed(rows('inputs/cost-kover-001/scenario_summary.csv'),['profile','network','author_scenario','scenario_id'])
    overlay=keyed(rows('runs/kover_accounting_v1/context21_overlay.csv'),['candidate_id','author_scenario','scenario_id'])
    assert len(overlay)==40
    audit=[]; hold=[]; controls=[]
    for (n,sc),r in results.items():
        ff=selected_flights(flights,r)
        ss=[s for s in sales if(s['profile'],s['network'],s['scenario'])==(r['source_profile'],r['source_network'],sc)]
        for policy in defs['scenarios']:
            x=overlay[n,sc,policy['id']]
            assert x['actual_full_budget']==x['actual_full_cash_peak']==''
            assert x['decision_status']=='AGENT_PROPOSAL'
            near(x['baseline_contribution'],r['contribution_before_base_fleet_opportunity'],'adapter40:baseline')
            assert (x['source_profile'],x['source_network'])==(r['source_profile'],r['source_network'])
            if n=='D_SVX8':
                assert len(ff)==16 and not any('UFA' in (f['origin'],f['destination']) for f in ff)
                near(x['overlay_delta'],0,'DSVX8_own16:zero');near(x['remaining_journeys'],r['sold_journeys'],'DSVX8_own16:remaining')
                controls.append(dict(candidate=n,scenario=sc,policy=policy['id'],own_flights=16,UFA_endpoints=0,delta=0))
                continue
            key=(r['source_profile'],r['source_network'],sc,policy['id']); s=fixed[key]
            assert x['correction_commit']==TIMEFIX and x['independent_correction_review']=='NOT_RUN'
            assert 'PARENT_TIMEBASE_AND_DELTA_CHECK_ONLY' in s['acceptance_scope']
            for k,val in [('source_commit','93fa5cf4a10ab67e05c93d19fc5375fc58ef9299'),('period_start','2026-12-07'),('period_end','2026-12-13')]:assert s[k]==val
            if policy['action']=='delay' and n.startswith('H_UFA'):
                for k in ['overlay_delta','contribution_after_before_unknown','unserved_journeys','remaining_journeys','additional_cash_peak_net_fixture']:assert x[k]==''
                assert x['delay_status']=='HOLD_RESOURCE_CONFLICT'
                assert s['overlay_delta_before_unknown_rub']==''
                assert s['hypothetical_overlay_delta_before_unknown_rub_if_recovered']!=''
                hold.append(dict(candidate=n,scenario=sc,status=x['delay_status'],accepted_money=None,accepted_served=None))
            else:
                for k,sk in [('overlay_delta','overlay_delta_before_unknown_rub'),('contribution_after_before_unknown','contribution_after_overlay_before_unknown_rub'),('remaining_journeys','remaining_endpoint_journeys'),('unserved_journeys','unserved_endpoint_journeys'),('additional_cash_peak_net_fixture','additional_cash_peak_timing_stress_rub')]:near(x[k],s[sk],'adapter40:projection')
                near(s['overlay_delta_before_unknown_rub'],original[key]['overlay_delta_before_unknown_rub'],'adapter40:original_delta')
            if policy['action']=='cancel':
                v,aff,cost=cancellation(ss,ff,params[sc],defs['avoidability_profiles'][policy['avoidability']],defs)
                for k,sk in [('delta','overlay_delta_before_unknown_rub'),('affected_journeys','unserved_endpoint_journeys'),('lost_fare_once','lost_net_revenue_rub'),('cancelled_legs','cancelled_physical_legs'),('unserved_segments','unserved_segment_allocations')]:near(v[k],s[sk],'C12:'+k)
                for k,val in cost.items():near(val,s['saved_'+k+'_rub'],'C12:component_'+k)
                near(v['delta'],x['overlay_delta'],'C12:adapter_delta')
                near(float(r['contribution_before_base_fleet_opportunity'])+v['delta'],x['contribution_after_before_unknown'],'C12:accrual')
                audit.append(dict(candidate=n,scenario=sc,policy=policy['id'],saved_fuel_product=cost['fuel_product'],saved_other=v['avoidable_costs']-cost['fuel_product'],**v))
    assert len(audit)==12 and len(hold)==4 and len(controls)==10
    save('independent_adapter_cancellations12.csv',audit);save('held_delays.json',hold);save('DSVX8_controls.csv',controls)
    cash=rows('inputs/cost-timebase-002/cash_fixture.csv');cashchecks=[];eventsout=[]
    for n,sc,pol in itertools.product(['H_UFA_4','H_UFA_8'],['base','cautious'],[p['id'] for p in defs['scenarios'] if p['action']=='cancel']):
        events=[e for e in cash if(e['network'],e['author_scenario'],e['scenario_id'])==(n,sc,pol)]
        keyed(events,['relative_day','event']);balance=0;trough=0;pnlsum=0
        primitive=next(a for a in audit if(a['candidate'],a['scenario'],a['policy'])==(n,sc,pol))
        assert len(events)==4
        timing=defs['cash_timing_stress']
        expected={
            'scheduled_service_not_provided':(timing['service_relative_day'],primitive['delta'],primitive['saved_fuel_product'],-primitive['saved_other'],primitive['lost_fare_once'],0),
            'avoided_conditional_usage_settlement':(timing['supplier_settlement_relative_day'],0,0,primitive['saved_other'],0,primitive['saved_other']),
            'refund_precollected_net_fare_once':(timing['refund_relative_day'],0,0,0,-primitive['lost_fare_once'],-primitive['lost_fare_once']),
            'later_replenishment_reduced_conditionally':(timing['fuel_replenishment_relative_day'],0,-primitive['saved_fuel_product'],0,0,primitive['saved_fuel_product'])}
        for e in sorted(events,key=lambda e:(float(e['relative_day']),e['event'])):
            for k,val in zip(['relative_day','delta_pnl_rub','delta_inventory_rub','delta_payables_rub','delta_deferred_ticket_liability_rub','delta_cash_rub'],expected[e['event']]):near(e[k],val,'cash8:from_cancel_primitives_'+k)
            delta=float(e['delta_pnl_rub'])-float(e['delta_inventory_rub'])+float(e['delta_payables_rub'])+float(e['delta_deferred_ticket_liability_rub'])
            near(delta,e['delta_cash_rub'],'cash8:bridge');balance+=delta;pnlsum+=float(e['delta_pnl_rub']);trough=min(trough,balance)
            near(balance,e['cumulative_delta_cash_rub'],'cash8:balance');near(-trough,e['additional_funding_so_far_rub'],'cash8:funding')
            eventsout.append(dict(candidate=n,scenario=sc,policy=pol,day=e['relative_day'],event=e['event'],delta_cash=delta,cumulative_cash=balance,delta_pnl=float(e['delta_pnl_rub'])))
        x=overlay[n,sc,pol];near(balance,x['overlay_delta'],'cash8:terminal');near(pnlsum,x['overlay_delta'],'cash8:pnl_once');near(-trough,x['additional_cash_peak_net_fixture'],'cash8:peak')
        cashchecks.append(dict(candidate=n,scenario=sc,policy=pol,events=len(events),final_cash=balance,final_pnl=pnlsum,additional_net_fixture_funding=-trough,actual_company_cash=None))
    save('independent_cash8.csv',cashchecks);save('independent_cash_events.csv',eventsout)
    thresholds=[]
    for x in audit:
        if not x['candidate'].startswith('H_UFA'):continue
        n=x['candidate'];sc=x['scenario'];r=results[n,sc]
        diff=float(r['contribution_before_base_fleet_opportunity'])+x['delta']-float(results['D_previous_best8',sc]['contribution_before_base_fleet_opportunity'])
        q=x['affected_journeys']
        thresholds.append(dict(candidate=n,scenario=sc,policy=x['policy'],journeys=q,
                               cancel_burden_threshold=x['delta']/q,relative_difference=diff,relative_burden_threshold=diff/q,
                               author5000stress=diff-5000*q,B=None,deltaO=None,
                               formula='relative_difference - theta*journeys - B - deltaO = 0'))
    target=keyed(rows('runs/kover_accounting_v1/burden_thresholds.csv'),['candidate_id','scenario','policy'])
    for x in thresholds:
        r=target[x['candidate'],x['scenario'],x['policy']]
        for k,f in [('cancel_burden_threshold','extra_burden_per_unserved_to_erase_cancel_accrual_delta'),('relative_difference','difference_vs_previous8_before_fixed'),('relative_burden_threshold','extra_burden_per_unserved_for_relative_equality_before_fixed'),('author5000stress','same_burden5000_per_journey_difference')]:near(x[k],r[f],'threshold8:'+k)
    save('independent_thresholds8.csv',thresholds)


def allocate(ss, cc, ff, p, scenario, law):
    """Independent explicit directed-OD/flight ledger; returns totals and audits."""
    keyed(cc,['flight_id']);keyed(ff,['id']);keyed(ss,['flight_ids'])
    assert {c['flight_id'] for c in cc}=={f['id'] for f in ff}=={i for s in ss for i in s['flight_ids'].split(';')}
    fdict={f['id']:f for f in ff}; groups=collections.defaultdict(list)
    for s in ss:groups[s['origin'],s['destination']].append(s)
    for g in groups.values():
        for field in ['D','fare_once','transfer','known_direct_RW_capacity']:assert len({s[field] for s in g})==1
    knownpairs={tuple(sorted((s['origin'],s['destination']))) for s in ss if s['known_direct_RW_capacity'] and float(s['known_direct_RW_capacity'])>0}
    claims=[]
    for s in ss:
        direction=(s['origin'],s['destination']);g=groups[direction];legs=s['flight_ids'].split(';');trans=s['transfer']=='True'
        if law=='D_GUARD_STANDALONE_CLAIMS':
            component=legs[0].split('|')[0];freq=sum(x['flight_ids'].split('|')[0]==component for x in g);divisor=freq
        elif law=='COUNT_DISTINCT_DEPARTURE_TIMES':
            freq=len({(fdict[x['flight_ids'].split(';')[0]]['date'],fdict[x['flight_ids'].split(';')[0]]['departure_utc_minute']) for x in g});divisor=len(g)
        else:freq=divisor=len(g)
        share=(.45 if scenario=='base' else .30)*(1-math.exp(-freq/3))*(.65 if trans else 1)/divisor
        can=(.6 if scenario=='base' else .8) if tuple(sorted(direction)) in knownpairs else (.05 if scenario=='base' else .1)
        fare=float(s['fare_once']);oldfare=fare/(p['transfer_fare_factor'] if trans else 1)*p['old_RW_fare_ratio']
        rank=(trans,-(fare-can*oldfare-len(legs)*p['pax_cost'])/len(legs),*direction,int(s['day']),tuple(legs))
        claims.append((rank,s,legs,float(s['D'])*share,can,oldfare))
    remaining={c['flight_id']:float(c['capacity_scenario']) for c in cc};occupied=collections.Counter();market=collections.Counter();oldremaining={k:float(v[0]['known_direct_RW_capacity'] or 0) for k,v in groups.items()}
    total=collections.Counter();detail=[]
    for _,s,legs,claim,can,oldfare in sorted(claims,key=lambda x:x[0]):
        direction=(s['origin'],s['destination']);limits=[claim]+[remaining[i] for i in legs]
        if law=='D_GUARD_STANDALONE_CLAIMS':limits.append(max(0,float(s['D'])-market[direction]))
        sold=min(limits);assert sold>=0
        for leg in legs:remaining[leg]-=sold;occupied[leg]+=sold
        direct=min(sold*can,oldremaining[direction]);oldremaining[direction]-=direct;unknown=sold*can-direct
        vals=dict(sold_journeys=sold,transfer_journeys=sold if s['transfer']=='True' else 0,segment_pax=sold*len(legs),
                  migrated_RW_total=sold*can,migrated_RW_direct=direct,migrated_RW_unverified_connecting=unknown,
                  gross_revenue=sold*float(s['fare_once']),foregone_RW_revenue=sold*can*oldfare,
                  new_pax_variable=sold*len(legs)*p['pax_cost'],saved_old_pax_variable=(direct+2*unknown)*p['pax_cost'])
        total.update(vals);market[direction]+=sold
        detail.append(dict(origin=s['origin'],destination=s['destination'],flight_ids=s['flight_ids'],**vals))
    for c in cc:
        f=fdict[c['flight_id']];near(sum(components(f,p).values()),c['flight_variable_cost'],'portfolio90:flightcost')
        near(occupied[c['flight_id']]+remaining[c['flight_id']],c['capacity_scenario'],'portfolio90:seat_each_flight')
        assert -1e-8<=remaining[c['flight_id']]<=float(c['capacity_scenario'])+1e-8
    for k,g in groups.items():assert market[k]<=float(g[0]['D'])+1e-8 and oldremaining[k]>=-1e-8
    total['flight_variable_cost']=sum(float(c['flight_variable_cost']) for c in cc)
    total['incremental_revenue']=total['gross_revenue']-total['foregone_RW_revenue']
    total['contribution_before_base_fleet_opportunity']=total['incremental_revenue']-total['flight_variable_cost']-total['new_pax_variable']+total['saved_old_pax_variable']
    total['load_factor']=total['segment_pax']/sum(float(c['capacity_scenario']) for c in cc)
    total['net_new_RW_journeys_scenario']=total['sold_journeys']-total['migrated_RW_total']
    near(sum(occupied.values()),total['segment_pax'],'portfolio90:segment_sum')
    return total,detail,occupied,market


def run_portfolio(flights,sales,caps,params,results):
    published=keyed(rows('runs/portfolio_v2/summary.csv'),['portfolio','scenario','capture_law'])
    assert len(published)==90
    prior=keyed(rows('runs/portfolio_v1/summary.csv',PRIOR),['portfolio','scenario','capture_law'])
    candidates=sorted({k[0] for k in results});output=[];guards=[];seatrows=[];cal=[]
    pair_details=keyed(rows('runs/portfolio_v2/pair_portfolio_itineraries.csv'),['portfolio','scenario','capture_law','flight_ids'])
    for count in range(1,5):
        for subset in itertools.combinations(candidates,count):
            pid='+'.join(subset)
            for sc in ['base','cautious']:
                ss=[];cc=[];ff=[]
                for n in subset:
                    r=results[n,sc];key=(r['source_profile'],r['source_network'])
                    for s in sales:
                        if (s['profile'],s['network'],s['scenario'])==(*key,sc):ss.append(dict(s,flight_ids=';'.join(n+'|'+i for i in s['flight_ids'].split(';'))))
                    for c in caps:
                        if (c['profile'],c['network'],c['scenario'])==(*key,sc):cc.append(dict(c,flight_id=n+'|'+c['flight_id']))
                    for f in selected_flights(flights,r):ff.append(dict(f,id=n+'|'+f['id'],aircraft=n+'|'+f['aircraft']))
                for law in ['D_GUARD_STANDALONE_CLAIMS','COUNT_ALL_OFFERS','COUNT_DISTINCT_DEPARTURE_TIMES']:
                    total,detail,occupied,markets=allocate(ss,cc,ff,params[sc],sc,law)
                    x=published[pid,sc,law]
                    for field in TOTAL:near(total[field],x[field],'portfolio90:'+field)
                    working=sum(int(results[n,sc]['active_allocated']) for n in subset)
                    near(x['working_required'],working,'portfolio90:tails');near(x['reserve_assumption'],1,'portfolio90:reserve')
                    near(x['new_UFA_base_count'],int(any(n.startswith('H_UFA') for n in subset)),'portfolio90:base_once')
                    assert x['full_budget']=='' and x['decision_status']=='AGENT_PROPOSAL'
                    additive=sum(float(results[n,sc]['contribution_before_base_fleet_opportunity']) for n in subset)
                    near(additive,x['additive_component_contribution'],'portfolio90:additive')
                    if law=='D_GUARD_STANDALONE_CLAIMS':
                        delta=total['contribution_before_base_fleet_opportunity']-additive;near(delta,0,'D30:delta_zero')
                        guards.append(dict(portfolio=pid,scenario=sc,delta=delta,standalone=additive,hardD=total['contribution_before_base_fleet_opportunity']))
                    else:
                        for field in TOTAL:near(x[field],prior[pid,sc,law][field],'prior60:'+field)
                    if len(subset)==2:
                        for d in detail:
                            ref=pair_details[pid,sc,law,d['flight_ids']]
                            for field in MONEY+QUANT:near(d[field],ref[field],'portfolio_pair_detail:'+field)
                    for c in cc:seatrows.append(dict(portfolio=pid,scenario=sc,law=law,flight_id=c['flight_id'],capacity=float(c['capacity_scenario']),occupied=occupied[c['flight_id']]))
                    output.append(dict(portfolio=pid,scenario=sc,law=law,working_required=working,reserve=1,**total))
    assert len(guards)==30
    # Calendar rows are checked once per candidate/scenario, not inferred from labels.
    for (n,sc),r in results.items():
        ff=selected_flights(flights,r)
        for tail in sorted({f['aircraft'] for f in ff}):
            ordered=sorted([f for f in ff if f['aircraft']==tail],key=lambda f:float(f['departure_utc_minute']))
            gaps=[]
            for a,b in zip(ordered,ordered[1:]):
                assert a['destination']==b['origin'];gap=float(b['departure_utc_minute'])-float(a['arrival_utc_minute']);assert gap>=45;gaps.append(gap)
            cal.append(dict(network=n,scenario=sc,tail_namespace=n+'|'+tail,legs=len(ordered),minimum_turn_minutes=min(gaps) if gaps else None))
    save('independent_portfolio90.csv',output);save('independent_guard30.csv',guards);save('independent_flight_seats.csv',seatrows);save('independent_calendar.csv',cal)


def preservation():
    checks=[]
    for directory,sha in [('runs/common_demand_v1/',COMMON),('runs/common_demand_v1/',PRIOR),('runs/portfolio_v1/',PRIOR)]:
        files=subprocess.check_output(['git','ls-tree','-r','--name-only',sha,PREFIX+directory],cwd=REPO,text=True).splitlines()
        for p in files:
            before=raw(p,sha,True);after=raw(p,SUBJECT,True);assert before==after
            checks.append(dict(path=p,reference_commit=sha,byte_equal=True,sha256=hashlib.sha256(before).hexdigest()))
    for name in ['summary.csv','calendar_checks.csv','case_checks.csv','pair_portfolio_itineraries.csv','shared_market_audit.csv','validation.json']:
        a=raw('runs/portfolio_v1/'+name,PRIOR);b=raw('runs/portfolio_v1_replay/'+name)
        if name.endswith('.csv'):
            aa=list(csv.DictReader(io.StringIO(a.decode())));bb=list(csv.DictReader(io.StringIO(b.decode())))
            assert sorted(tuple(sorted(r.items())) for r in aa)==sorted(tuple(sorted(r.items())) for r in bb)
        else:assert json.loads(a)==json.loads(b)
        checks.append(dict(path='runs/portfolio_v1_replay/'+name,reference_commit=PRIOR,byte_equal=a==b,values_equal=True))
    save('preservation.json',checks)


def subject_manifest_check():
    manifest=obj('output_manifest.json');checked=[]
    scoped=['runs/common_demand_v1/','runs/portfolio_v1/','runs/portfolio_v1_replay/','runs/portfolio_v2/','runs/kover_accounting_v1/','runs/kover_demand_v1/']
    code={'common_demand.py','portfolio_comparison.py','integrate_kover_accounting.py','kover_demand_interaction.py','portfolio_guard_comparison.py','kover_demand_contract.json','portfolio_guard_contract.json','integration_readout.md'}
    for entry in manifest['files']:
        p=entry['path']
        if p in code or any(p.startswith(prefix) for prefix in scoped):
            b=raw(p);assert hashlib.sha256(b).hexdigest()==entry['sha256'] and len(b)==entry['bytes']
            checked.append(dict(path=p,hash_matches=True,bytes=len(b)))
    assert len(checked)>=45
    save('subject_manifest_check.json',dict(status='PASS_SCOPED_SUBJECT_MANIFEST',checked=checked,outside_scope='Rest of owner package not reaccepted'))


def main():
    for p in ['contract.md','briefs/methods_integration_review.md']:raw('context/23_night_run_20261110/'+p,ROOT,True)
    for p in ['integration_readout.md','requests.json','kover_demand_contract.json','portfolio_guard_contract.json','common_demand.py','portfolio_comparison.py','integrate_kover_accounting.py','kover_demand_interaction.py','portfolio_guard_comparison.py','qualify_review_inputs.py','runs/admission_v1/acceptance_matrix.csv']:raw(p)
    # Review anchors are external historical results, not today's own PASS.
    for sha,folder in [('7a868d1282b9c4de012e39e9fc1104d2d7f675e4','common_comparison_review'),('0cc043484147cb9f3a23a3d3d2aea9b4a6ce9ed9','strategy_accounting_review'),('d8634187d452343a369f7cec63be50511bb70020','cost_kover_review')]:
        raw('context/23_night_run_20261110/'+folder+'/handoff.json',sha,True)
    params=obj(SRC+'15_team_update/model/configuration.json')['scenarios']
    flights=rows(SRC+'17_aircraft_route_review/model/flights.csv');sales=rows(SRC+'17_aircraft_route_review/model/sales.csv');caps=rows(SRC+'17_aircraft_route_review/model/capacity.csv')
    results=keyed(rows(SRC+'21_team_proposals/comparison.csv'),['network','scenario'])
    for name in ['17_aircraft_route_review/model/flights.csv','17_aircraft_route_review/model/sales.csv','17_aircraft_route_review/model/capacity.csv','21_team_proposals/comparison.csv','15_team_update/model/configuration.json']:
        assert raw(SRC+name)==raw('context/'+name,'93fa5cf4a10ab67e05c93d19fc5375fc58ef9299',True)
    defs=obj('inputs/cost-kover-001/scenario_definitions.json')
    run_cancellation(flights,params,results,defs)
    run_adapter(flights,sales,params,results,defs)
    run_portfolio(flights,sales,caps,params,results)
    preservation()
    subject_manifest_check()
    save('source_manifest.json',dict(subject=SUBJECT,read_method='git show <exact SHA>:<path>; no moving folders, remote APIs, raw reparsing or new forecasts',sources=list(RECEIPTS.values())))
    save('checks.json',dict(status='PASS_INDEPENDENT_ORACLE',comparisons=dict(CHECKS),cancellation_cases=16,adapter_rows=40,held_delays=4,adapter_cancellation_ledgers=12,cash_ledgers=8,portfolio_rows=90,D_guard_cases=30,prior_portfolio_cases=60,
         acceptance=['RAW_HASH_VERIFIED_FOR_EXACT_GIT_INPUTS','JOIN_CHECKED','CONSERVATION_PASS','CONDITIONAL_ECONOMICS_CHECKED'],
         outside_scope=['MR08 full boundaries','MR09 resource/product modules','MR10 raw/source/timebase correction reacceptance','observed OD','full budget or company cash','legal compensation','network optimum or launch']))
    print(json.dumps(dict(status='PASS_INDEPENDENT_ORACLE',comparisons=sum(CHECKS.values()),source_objects=len(RECEIPTS))))


if __name__=='__main__':main()
