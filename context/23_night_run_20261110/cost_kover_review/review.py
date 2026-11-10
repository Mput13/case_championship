#!/usr/bin/env python3
"""Independent, offline review of the exact MR02 delivery, stdlib only.

All source bytes come from git show <full SHA>:<path>. No author main, moving
branch, peer folder, market search, network selector or self-check is executed.
Frozen overlay functions are invoked separately as the system under test.
"""
import ast
import collections
import copy
import csv
import hashlib
import io
import json
import math
import subprocess
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

DELIVERY = 'afadee35ebeefe54a05bdfc5b3e224a370f90e0a'
PAYLOAD = '553e63a5de32cff941fde3ca28175f242f28375c'
BASE = 'f1774e1f66a9483fb618ca6003abd9dc4d8563e1'
PREFIX = 'context/23_night_run_20261110/cost_kover/'
OUT = Path(__file__).resolve().parent
UTC = timezone.utc
READS = {}
CHECKS = []
COMPONENTS = ('fuel_product', 'fuel_uplift', 'mro', 'crew', 'navigation', 'airport_turn', 'deicing')
GRAINS = {
    'tsiri_flights.csv':'profile x alternative programme x physical flight_id; absolute week minutes',
    'flights.csv':'author profile x alternative programme x physical flight_id; absolute week minutes',
    'tsiri_sales.csv':'profile x alternative programme x author scenario x endpoint OD x dated itinerary; original CSV row',
    'sales.csv':'author profile x alternative programme x author scenario x endpoint OD x dated itinerary',
    'tsiri_capacity.csv':'profile x alternative programme x author scenario x physical flight_id',
    'capacity.csv':'profile x alternative programme x author scenario x physical flight_id',
    'tsiri_comparison.csv':'profile x alternative programme x author scenario; not additive alternatives',
    'comparison.csv':'author alternative programme x scenario aggregate',
    'principal_calendar.csv':'repaired reference alternative programme x physical flight_id; absolute week minutes',
    'itinerary_sales.csv':'repaired reference programme x author scenario x endpoint OD x dated itinerary',
    'flight_capacity.csv':'repaired reference programme x author scenario x physical flight_id',
    'nastya_network.csv':'author network parameter; base/cautious in separate columns',
    'core_registry.csv':'dataset_id x captured public source snapshot',
    'source_registry.csv':'dataset_id x captured public source snapshot',
    'primary_ufa_oms.csv':'airport x selected service rate x unit x effective date',
    'airport_cost_selected_verified.csv':'airport x selected service rate x unit x effective date',
    'khv_cost_components.csv':'KHV PDF version x selected service item x unit x effective date',
    'input_registry.csv':'author parameter x base/cautious x unit x provenance',
    'tsiri_cost_registry.csv':'author parameter x base/cautious x unit x provenance',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


@lru_cache(None)
def gitbytes(commit, path):
    data = subprocess.check_output(['git', 'show', commit + ':' + path])
    READS[(commit, path)] = dict(source_commit=commit, source_path=path,
        sha256=digest(data), size_bytes=len(data), acquisition='git show exact SHA:path',
        grain=GRAINS.get(Path(path).name,'pinned code/document or named scenario/configuration snapshot'))
    return data


def b(path, commit=DELIVERY):
    return gitbytes(commit, PREFIX + path)


def s(path):
    return b(path).decode('utf-8-sig')


def j(path):
    return json.loads(b(path))


def rows(path):
    return list(csv.DictReader(io.StringIO(s(path))))


def jsonout(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def csvout(name, records):
    records = list(records)
    fields = list(dict.fromkeys(k for r in records for k in r))
    with (OUT / name).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fields, lineterminator='\n')
        w.writeheader()
        w.writerows(records)


def eq(a, z, label=''):
    assert math.isfinite(float(a)) and math.isfinite(float(z)), (label, a, z)
    assert math.isclose(float(a), float(z), abs_tol=1e-6, rel_tol=1e-12), (label, a, z)


def total(records, field):
    return math.fsum(float(r[field]) for r in records)


def checked(id, detail, count=None):
    CHECKS.append(dict(id=id, status='PASS', detail=detail, count=count,
        performed_by='this independent reviewer', acceptance_scope='EXACT_INPUT_OFFLINE_ONLY'))


def verify_inputs():
    gitbytes(BASE, 'context/23_night_run_20261110/contract.md')
    gitbytes(BASE, 'context/23_night_run_20261110/briefs/cost_kover_review.md')
    manifest = j('output_manifest.json')
    for r in manifest['files']:
        data = b(r['path'])
        if Path(r['path']).name not in GRAINS:
            READS[(DELIVERY,PREFIX+r['path'])]['grain']=r.get('grain','named pinned payload item')
        assert digest(data) == r['sha256'] and len(data) == r['size_bytes'], r
        assert data == b(r['path'], PAYLOAD), r['path']
    assert digest('\n'.join(r['path'] + '\t' + r['sha256'] for r in manifest['files']).encode()) == manifest['aggregate_sha256']
    assert j('handoff.json')['payload_commit'] == PAYLOAD
    assert j('handoff.json')['payload_manifest_sha256'] == digest(b('output_manifest.json'))
    changed = subprocess.check_output(['git', 'diff', '--name-only', PAYLOAD, DELIVERY, '--', PREFIX], text=True).splitlines()
    assert changed == [PREFIX + 'handoff.json'], changed
    sourcechecks = []
    for file in ['source_manifest.json', 'reference_input_manifest.json']:
        for r in j(file)['sources']:
            if r.get('publication') == 'LOCAL_IGNORED_ONLY':
                sourcechecks.append(dict(id=r['id'], scope='PRIMARY_RAW_CHECKED_SEPARATELY', sha256=r['sha256']))
                continue
            data = b(r['local_path'])
            assert digest(data) == r['sha256'] and len(data) == r['size_bytes'], r
            if r.get('source_commit'):
                assert data == gitbytes(r['source_commit'], r['source_path']), r
                kind = 'BYTE_EQUAL_TO_EXACT_UPSTREAM_GIT_SOURCE'
            else:
                kind = 'PINNED_PARENT_SNAPSHOT_HASH_ONLY_NO_UPSTREAM_GIT_IDENTITY'
            sourcechecks.append(dict(id=r.get('id', r['local_path']), scope=kind, sha256=r['sha256'], source_commit=r.get('source_commit')))
    jsonout('input_verification.json', dict(payload_files=len(manifest['files']),
        payload_aggregate_sha256=manifest['aggregate_sha256'], changed_between_payload_and_delivery=changed,
        source_checks=sourcechecks, no_author_self_checks_executed=True,
        baseline_bytes='all manifest inputs personally compared to pinned upstream bytes where source_commit exists'))
    checked('CKR01', 'Payload hashes, delivery/payload delta and upstream frozen source bytes verified', len(manifest['files']))


def scenario_parameters(sc):
    data = j('inputs/tsiri_inputs.json')
    return {**data['scenarios'][sc], **j('inputs/tsiri_overrides.json').get('scenarios', {}).get(sc, {})}, data['ufa_reference_basket_rub']


def components(leg, sc):
    p, basket = scenario_parameters(sc)
    hours = float(leg['block_minutes']) / 60
    tonnes = hours * p['fuel_t_per_hour'] + p['fuel_t_per_cycle']
    return dict(fuel_product=tonnes * p['fuel_rub_per_t'], fuel_uplift=tonnes * p['fuel_uplift_rub_per_t'],
        mro=hours * p['mro_rub_per_hour'], crew=hours * p['crew_rub_per_hour'],
        navigation=hours * p['navigation_rub_per_hour'], airport_turn=basket * p['airport_factor'],
        deicing=p['deicing_probability'] * p['deicing_operation_rub'])


def extract_function(path, name, cls=None, namespace=None):
    code = s(path)
    tree = ast.parse(code)
    body = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == cls).body if cls else tree.body
    node = next(x for x in body if isinstance(x, ast.FunctionDef) and x.name == name)
    ns = {} if namespace is None else dict(namespace)
    exec(compile(ast.Module(body=[node], type_ignores=[]), DELIVERY + ':' + PREFIX + path, 'exec'), ns)
    return ns[name]


def verify_parameters():
    params, provenance = rows('cost_parameters.csv'), rows('parameter_provenance.csv')
    byid = {r['parameter_id']: r for r in params}
    prov = {r['parameter_id']: r for r in provenance}
    assert len(params) == len(byid) == len(prov) == 117 and set(byid) == set(prov)
    registry = {r['parameter']: r for r in rows('inputs/tsiri_cost_registry.csv')}
    primary = rows('inputs/primary_ufa_oms.csv')
    khv = rows('inputs/khv_cost_components.csv')
    urls = {r['dataset_id']: r for r in rows('inputs/core_registry.csv')}
    nastya = {r['parameter']: r for r in rows('inputs/nastya_network.csv')}
    public = {'PUBLIC:' + r['source_dataset_id'] + ':' + r['item']: r for r in primary}
    khvmap = {'PUBLIC:' + r['source_id'] + ':' + r['component_id']: r for r in khv}
    fixed = j('inputs/tsiri_stage16_assumptions.json')
    verified = []
    for id, r in byid.items():
        parts = id.split(':')
        q = prov[id]
        assert digest(b(q['snapshot'])) == q['input_file_sha256'], id
        status = 'INPUT_VALUE_UNIT_AND_PROVENANCE_CHECKED'
        if parts[0] == 'TSIRI':
            p, basket = scenario_parameters(parts[1]); key = parts[2]
            expected = basket * p['airport_factor'] if key == 'airport_turn_basket' else p[key]
            eq(r['value'], expected, id)
            if key in registry:
                assert r['unit'] == registry[key]['unit']
                eq(r['value'], registry[key][parts[1]], id)
            assert r['value_status'] == 'AUTHOR_INPUT_NOT_CONTRACT'
        elif parts[0] == 'NASTYA':
            eq(r['value'], nastya[parts[2]][parts[1]], id)
            assert r['unit'] == nastya[parts[2]]['unit']
            assert r['tax_basis'] == 'UNKNOWN'
        elif id in public:
            source = public[id]; upstream = urls[source['source_dataset_id']]
            eq(r['value'], source['value'], id)
            for a, z in [('unit', 'unit'), ('airport', 'airport_iata'), ('effective_from', 'effective_from'), ('known_on', 'known_on'), ('tax_basis', 'VAT_basis')]:
                assert r[a] == source[z], (id, a)
            assert q['upstream_url'] == upstream['source_url'] and q['primary_raw_sha256'] == upstream['sha256'], id
            status = 'INHERITED_UFA_OMS_EXTRACT_PERSONALLY_JOINED_NOT_RAW_REVIEWED'
        elif id in khvmap:
            source = khvmap[id]
            eq(r['value'], source['value'], id)
            for a,z in [('unit','unit'),('tax_basis','vat_basis'),('effective_from','effective_from')]: assert r[a] == source[z]
            assert q['upstream_url'] == source['source_url'] and q['primary_raw_sha256'] == source['source_sha256']
            status = 'KHV_EXTRACT_JOINED_SELECTED_ROWS_PERSONALLY_VISUALLY_REVIEWED'
        elif parts[0] == 'UNKNOWN':
            assert r['value'] == '' and r['missing_reason'] and r['value_status'] == 'UNKNOWN'
            status = 'UNKNOWN_PRESERVED_NO_ZERO_OR_SOURCE_ACCEPTANCE'
        elif parts[0] == 'AUTHOR_FIXED_SCENARIO':
            eq(r['value'], fixed[parts[1]], id)
            assert r['value_status'] == 'NOT_EMPIRICAL_NOT_APPLIED'
        else:
            raise AssertionError(id)
        verified.append(dict(parameter_id=id, value=r['value'], unit=r['unit'], status=status,
            snapshot=q['snapshot'], snapshot_sha256=q['input_file_sha256'], actual_RW_contract='UNKNOWN'))
    unknowns = [r for r in params if r['parameter_id'].startswith('UNKNOWN:')]
    assert len(unknowns) == 25 and len(rows('budget_terms.csv')) == 25
    assert all(r['value'] == '' for r in rows('budget_terms.csv'))
    assert all(r['statistical_interval'] == 'False' and r['confidence_level'] == '' for r in rows('range_registry.csv'))
    # Independent arithmetic and function replay for Anastasia: fuel includes uplift already.
    fn = extract_function('inputs/nastya_network_model.py', 'leg_cost')
    testrows = []
    for sc in ['base','cautious']:
        a = {k:float(v[sc]) for k,v in nastya.items() if v.get(sc) not in ('',None)}
        for km,south,pax in [(800,False,0),(1800,True,50),(2300,True,100)]:
            h = a['block_fixed_h'] + km * a['route_factor_south' if south else 'route_factor'] / a['block_speed_kmh']
            target = (h*a['fuel_t_per_hour']+a['fuel_t_per_cycle'])*a['fuel_rub_per_t'] + h*(a['mro_rub_per_hour']+a['crew_rub_per_hour']+a['navigation_rub_per_hour']) + a['ground_rub_per_flight']+a['deicing_rub_per_flight']+pax*a['pax_cost_rub']
            ah,av = fn(a,km,south,pax); eq(ah,h);eq(av,target)
            testrows.append(dict(scenario=sc,km=km,south=south,pax=pax,block_hours=h,variable_rub=target))
    p0,basket=scenario_parameters('base');p1,_=scenario_parameters('cautious')
    eq(basket,49.45*(553+499)+19300+8100+16668)
    eq(p0['fuel_rub_per_t']+p0['fuel_uplift_rub_per_t']-float(nastya['fuel_rub_per_t']['base']),3100)
    eq(p1['fuel_rub_per_t']+p1['fuel_uplift_rub_per_t'],float(nastya['fuel_rub_per_t']['cautious']))
    eq((700+609-562-445)*49.45,14933.9)
    eq(1051*24,25224)
    csvout('parameter_checks.csv',verified)
    csvout('independent_nastya_cost_samples.csv',testrows)
    checked('CKR02', 'All 117 registry values/units/lineage checked; 25 actual contract terms remain UNKNOWN',117)


def at(leg,event,origin):
    """Author minutes are absolute from WEEK; row date is a consistency check."""
    return origin + timedelta(minutes=float(leg[event+'_utc_minute']))


def exposed(leg,episode,origin):
    lo,hi=(datetime.fromisoformat(episode[k]) for k in ['start_utc','end_utc_exclusive'])
    if hi<lo: raise ValueError('negative interval')
    return (leg['origin']==episode['airport'] and lo<=at(leg,'departure',origin)<hi) or (leg['destination']==episode['airport'] and lo<=at(leg,'arrival',origin)<hi)


def occupancy(sales,legs,caps):
    ids={x['id'] for x in legs};assert len(ids)==len(legs)
    assert ids==set(caps)
    used=collections.defaultdict(float)
    for row in sales:
        links=row['flight_ids'].split(';');q=float(row['sold_journeys'])
        assert q>=0 and len(set(links))==len(links) and set(links)<=ids
        for id in links: used[id]+=q
    for id in ids:
        assert float(caps[id]['capacity_scenario'])>=0 and used[id]<=float(caps[id]['capacity_scenario'])+1e-6
    return used


def load_dataset(network,sc):
    d=j('scenario_definitions.json');profile=d['profile']
    sel=lambda r:r['profile']==profile and r['network']==network
    legs=[r for r in rows('inputs/tsiri_flights.csv') if sel(r)]
    sales=[dict(r,_source_csv_line=line,_journey_id='tsiri-sales-line-'+str(line))
        for line,r in enumerate(rows('inputs/tsiri_sales.csv'),2) if sel(r) and r['scenario']==sc]
    caps={r['flight_id']:r for r in rows('inputs/tsiri_capacity.csv') if sel(r) and r['scenario']==sc}
    baselines=[r for r in rows('inputs/tsiri_comparison.csv') if sel(r) and r['scenario']==sc]
    assert len(baselines)==1
    return legs,sales,caps,baselines[0]


def cash_direct(loss,savings,timing,fuel_cash_day=None):
    """Direct cash flows first, then stocks reconcile. One refund, no new loss."""
    fuel=savings['fuel_product'];other=math.fsum(savings.values())-fuel
    flows=collections.defaultdict(float)
    flows[0]+=0
    flows[timing['supplier_settlement_relative_day']]+=other
    flows[timing['refund_relative_day']]-=loss
    flows[timing['fuel_replenishment_relative_day'] if fuel_cash_day is None else fuel_cash_day]+=fuel
    balance=0;trough=0;events=[]
    for day,flow in sorted(flows.items()):
        balance+=flow;trough=min(trough,balance)
        events.append(dict(relative_day=day,delta_cash_rub=flow,cumulative_delta_cash_rub=balance))
    return events,-trough


def template_issues(legs,origin,shifted=None,cancelled=frozenset()):
    shifted=shifted or {};bylabel=collections.defaultdict(list)
    for r in legs:
        if r['id'] not in cancelled:bylabel[r['aircraft']].append(r)
    issues=[]
    for label,seq in bylabel.items():
        seq=sorted(seq,key=lambda r:at(r,'departure',origin)+timedelta(minutes=shifted.get(r['id'],0)))
        for left,right in zip(seq,seq[1:]):
            arr=at(left,'arrival',origin)+timedelta(minutes=shifted.get(left['id'],0))
            dep=at(right,'departure',origin)+timedelta(minutes=shifted.get(right['id'],0))
            spatial=left['destination']!=right['origin'];temporal=dep<arr+timedelta(minutes=45)
            if spatial or temporal:
                issues.append(dict(planning_label=label,left=left['id'],right=right['id'],
                    left_arrival_utc=arr.isoformat(),right_departure_utc=dep.isoformat(),
                    ground_minutes=(dep-arr).total_seconds()/60,spatial_discontinuity=spatial,
                    overlap_or_turn_violation=temporal,actual_tail='UNKNOWN'))
    return issues


def frozen_module():
    ns={'__name__':'frozen_overlay_under_review','__file__':str(OUT/'unwritten_overlay.py')}
    exec(compile(s('overlay.py'),DELIVERY+':'+PREFIX+'overlay.py','exec'),ns)
    ns['parameters']=scenario_parameters
    return SimpleNamespace(**ns)


def independent_overlays():
    definition=j('scenario_definitions.json');origin=datetime.fromisoformat(definition['period_start']).replace(tzinfo=UTC)
    source_tree=ast.parse(s('inputs/tsiri_core_model.py'))
    week=next(ast.literal_eval(n.value) for n in source_tree.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='WEEK' for t in n.targets))
    assert week==definition['period_start']=='2026-12-07'
    published={(r['network'],r['author_scenario'],r['scenario_id']):r for r in rows('scenario_summary.csv')}
    assert len(published)==40
    physical={(r['network'],r['author_scenario'],r['scenario_id'],r['flight_id']):r for r in rows('physical_leg_status.csv')}
    published_journeys={(r['network'],r['author_scenario'],r['scenario_id'],r['journey_id']):r for r in rows('affected_journeys.csv')}
    published_components={(r['network'],r['author_scenario'],r['flight_id'],r['component']):r for r in rows('author_flight_cost_components.csv')}
    cashrows=rows('cost_cash_bridge.csv');thresholds={(r['network'],r['author_scenario'],r['scenario_id']):r for r in rows('thresholds.csv')}
    core=extract_function('inputs/tsiri_core_model.py','flight_cost','Model')
    route=extract_function('inputs/tsiri_route_model.py','flight_cost','RouteModel',{'core':SimpleNamespace(Model=SimpleNamespace(flight_cost=core))})
    out=[];baselineout=[];journeyout=[];cashout=[];timeout=[];conflicts=[];counts=collections.Counter()
    for network in definition['networks']:
        for sc in definition['author_scenarios']:
            legs,sales,caps,base=load_dataset(network,sc);p,basket=scenario_parameters(sc)
            used=occupancy(sales,legs,caps)
            assert len(legs)==len(caps)
            for leg in legs:
                for event in ['departure','arrival']:
                    correct=at(leg,event,origin)
                    old=datetime.fromisoformat(leg['date']).replace(tzinfo=UTC)+timedelta(minutes=float(leg[event+'_utc_minute']))
                    assert datetime.fromisoformat(leg['date']).date()==(origin+timedelta(days=int(leg['day'])-1)).date()
                    if sc=='base':timeout.append(dict(network=network,flight_id=leg['id'],day=leg['day'],row_date=leg['date'],event=event,
                        absolute_utc_minute=leg[event+'_utc_minute'],published_instant_utc=old.isoformat(),correct_instant_utc=correct.isoformat(),error_minutes=(old-correct).total_seconds()/60))
                cc=components(leg,sc);fc=math.fsum(cc.values());eq(fc,caps[leg['id']]['flight_variable_cost'])
                obj=SimpleNamespace(scenarios={sc:p},old={'ufa_reference_basket_rub':basket},profile=definition['profile'])
                eq(route(obj,{**leg,'block_minutes':float(leg['block_minutes'])},sc),fc)
                for component,value in cc.items():eq(value,published_components[(network,sc,leg['id'],component)]['value_rub'])
                eq(used[leg['id']],caps[leg['id']]['occupied'])
            for row in sales:
                q=float(row['sold_journeys']);n=len(row['flight_ids'].split(';'))
                eq(q*float(row['fare_once']),row['gross_revenue'])
                eq(q*n,row['segment_pax']);eq(q*n*p['pax_cost'],row['new_pax_variable'])
                eq(float(row['migrated_RW_direct'])+float(row['migrated_RW_unverified_connecting']),row['migrated_RW_total'])
                eq((float(row['migrated_RW_direct'])+2*float(row['migrated_RW_unverified_connecting']))*p['pax_cost'],row['saved_old_pax_variable'])
                eq(float(row['gross_revenue'])-float(row['foregone_RW_revenue']),row['incremental_revenue'])
            for field in ['sold_journeys','transfer_journeys','segment_pax','gross_revenue','foregone_RW_revenue','incremental_revenue','new_pax_variable','saved_old_pax_variable']:
                eq(total(sales,field),base[field],(network,sc,field))
            flightcost=math.fsum(math.fsum(components(leg,sc).values()) for leg in legs)
            c=total(sales,'gross_revenue')-total(sales,'foregone_RW_revenue')-flightcost-total(sales,'new_pax_variable')+total(sales,'saved_old_pax_variable')
            eq(flightcost,base['flight_variable_cost']);eq(c,base['contribution_before_base_fleet_opportunity'])
            assert not template_issues(legs,origin),network
            baselineout.append(dict(profile=definition['profile'],network=network,author_scenario=sc,physical_legs=len(legs),
                itinerary_rows=len(sales),endpoint_journeys=total(sales,'sold_journeys'),segment_allocations=total(sales,'segment_pax'),
                gross_net_basis_fare_rub=total(sales,'gross_revenue'),flight_cost_rub=flightcost,contribution_rub=c,
                all_cost_components_and_capacity='PASS',actual_contract='UNKNOWN'))
            for policy in definition['scenarios']:
                key=(network,sc,policy['id']);reported=published[key]
                touched={r['id'] for r in legs if policy['episode_active'] and exposed(r,definition['episode'],origin)}
                cancelled=touched if policy['action']=='cancel' else set()
                impacted=[r for r in sales if touched.intersection(r['flight_ids'].split(';'))]
                lost=[r for r in sales if cancelled.intersection(r['flight_ids'].split(';'))]
                lostids={r['_journey_id'] for r in lost}
                remain=[r for r in sales if r['_journey_id'] not in lostids]
                savings={k:0. for k in COMPONENTS+('new_pax_variable',)}
                if cancelled:
                    shares=definition['avoidability_profiles'][policy['avoidability']]
                    for component in COMPONENTS:
                        savings[component]=math.fsum(components(r,sc)[component]*shares[component] for r in legs if r['id'] in cancelled)
                    savings['new_pax_variable']=total(lost,'new_pax_variable')*shares['new_pax_variable']
                loss=total(lost,'gross_revenue');delta=math.fsum(savings.values())-loss
                actual_used=collections.defaultdict(float)
                for r in remain:
                    for id in r['flight_ids'].split(';'):actual_used[id]+=float(r['sold_journeys'])
                calc=dict(affected_physical_legs=len(touched),cancelled_physical_legs=len(cancelled),
                    delayed_physical_legs=len(touched) if policy['action']=='delay' else 0,
                    affected_endpoint_journeys=total(impacted,'sold_journeys'),unserved_endpoint_journeys=total(lost,'sold_journeys'),
                    unserved_segment_allocations=total(lost,'segment_pax'),remaining_endpoint_journeys=total(remain,'sold_journeys'),
                    lost_net_revenue_rub=loss,overlay_delta_before_unknown_rub=delta,
                    contribution_after_overlay_before_unknown_rub=c+delta,
                    crew_cost_retained_rub=math.fsum(components(r,sc)['crew'] for r in legs),
                    **{'saved_'+k+'_rub':v for k,v in savings.items()})
                events,peak=cash_direct(loss,savings,definition['cash_timing_stress']) if policy['action']=='cancel' else ([dict(relative_day=0,delta_cash_rub=0,cumulative_delta_cash_rub=0)],0)
                calc['additional_cash_peak_timing_stress_rub']=peak
                for field,value in calc.items():eq(value,reported[field],(key,field))
                assert reported['full_budget_profit_rub']==reported['actual_full_cash_peak_rub']==''
                assert reported['actual_operational_readiness']=='UNKNOWN'
                for leg in legs:
                    r=physical[key+(leg['id'],)];cap=0 if leg['id'] in cancelled else float(caps[leg['id']]['capacity_scenario'])
                    for event in ['departure','arrival']:
                        old_time=datetime.fromisoformat(leg['date']).replace(tzinfo=UTC)+timedelta(minutes=float(leg[event+'_utc_minute']))
                        assert r['scheduled_'+event+'_utc']==old_time.isoformat()
                        if leg['id'] in touched and policy['action']=='delay':
                            assert r['conditional_actual_'+event+'_utc']==(old_time+timedelta(minutes=policy['delay_minutes'])).isoformat()
                    if r['scheduled_departure_utc']!=at(leg,'departure',origin).isoformat():counts['published_physical_rows_with_wrong_UTC_pair']+=1
                    eq(r['remaining_capacity'],cap);eq(r['remaining_occupied'],actual_used[leg['id']]);assert actual_used[leg['id']]<=cap+1e-6
                    eq(r['baseline_flight_cost_rub'],math.fsum(components(leg,sc).values()))
                    expected_saved=math.fsum(components(leg,sc)[k]*definition['avoidability_profiles'][policy['avoidability']][k] for k in COMPONENTS) if leg['id'] in cancelled else 0
                    eq(r['avoided_flight_cost_rub'],expected_saved)
                    counts['physical_rows_checked']+=1
                for r in impacted:
                    savedrow=published_journeys[key+(r['_journey_id'],)]
                    islost=r['_journey_id'] in lostids;q=float(r['sold_journeys'])
                    eq(savedrow['affected_leg_count'],len(touched.intersection(r['flight_ids'].split(';'))))
                    eq(savedrow['unserved_endpoint_journeys'],q if islost else 0)
                    eq(savedrow['lost_net_revenue_rub'],float(r['gross_revenue']) if islost else 0)
                    eq(savedrow['net_refund_cash_rub'],float(r['gross_revenue']) if islost else 0)
                    eq(savedrow['retained_net_fare_rub'],0 if islost else float(r['gross_revenue']))
                    eq(savedrow['old_foregone_revenue_unchanged_rub'],r['foregone_RW_revenue'])
                    eq(savedrow['saved_old_pax_unchanged_rub'],r['saved_old_pax_variable'])
                    journeyout.append(dict(network=network,author_scenario=sc,scenario_id=policy['id'],source_csv_line=r['_source_csv_line'],
                        origin=r['origin'],destination=r['destination'],flight_ids=r['flight_ids'],affected_leg_count=len(touched.intersection(r['flight_ids'].split(';'))),
                        affected_endpoint_journeys=q,lost_fare_once_rub=float(r['gross_revenue']) if islost else 0,actual_rebooking='UNKNOWN'))
                cs=[r for r in cashrows if (r['network'],r['author_scenario'],r['scenario_id'])==key]
                assert cs
                byday=collections.defaultdict(float)
                cumulative=0;minimum=0
                for r in cs:
                    cash=float(r['delta_cash_rub']);eq(cash,float(r['delta_pnl_rub'])-float(r['delta_inventory_rub'])+float(r['delta_payables_rub'])+float(r['delta_deferred_ticket_liability_rub']))
                    byday[float(r['relative_day'])]+=cash
                    cumulative+=cash;minimum=min(minimum,cumulative)
                    eq(r['cumulative_delta_cash_rub'],cumulative);eq(r['additional_funding_so_far_rub'],-minimum)
                eq(math.fsum(float(r['delta_pnl_rub']) for r in cs),delta)
                eq(math.fsum(byday.values()),delta)
                for ev in events:eq(byday[ev['relative_day']],ev['delta_cash_rub'])
                if policy['action']=='cancel':
                    refund=next(r for r in cs if r['event']=='refund_precollected_net_fare_once')
                    eq(refund['delta_pnl_rub'],0);eq(refund['delta_cash_rub'],-loss)
                    eq(total(cs,'delta_inventory_rub'),0);eq(total(cs,'delta_payables_rub'),0);eq(total(cs,'delta_deferred_ticket_liability_rub'),0)
                for ev in events:cashout.append(dict(network=network,author_scenario=sc,scenario_id=policy['id'],**ev,
                    timing_basis='CONDITIONAL_NET_TIMING_FIXTURE_ONLY',actual_full_reserve='UNKNOWN'))
                if policy['id']!='no_kover':
                    t=thresholds[key];eq(t['maximum_extra_cost_for_nonnegative_contribution_rub'],c+delta)
                    assert t['nonnegative_extra_cost_feasible']==str(c+delta>=0)
                shift={id:policy.get('delay_minutes',0) for id in touched} if policy['action']=='delay' else {}
                issues=template_issues(legs,origin,shift,cancelled)
                for issue in issues:conflicts.append(dict(network=network,author_scenario=sc,scenario_id=policy['id'],**issue))
                if policy['action']=='delay' and issues:counts['held_delay_combinations']+=1
                out.append(dict(profile=definition['profile'],network=network,author_scenario=sc,scenario_id=policy['id'],**calc,
                    arithmetic_match='PASS',correct_timebase_template_adjacent_conflicts=len(issues),
                    published_template_rotation_status=reported['template_rotation_status'],
                    reviewer_temporal_status='HOLD_CONFLICTING_TEMPLATE' if issues else 'LIMITED_TEMPLATE_CHECK_PASS',
                    full_budget_profit_rub=None,actual_full_cash_peak_rub=None))
    assert len(out)==40 and len(baselineout)==8
    assert len(journeyout)==len(published_journeys)==240
    assert counts['physical_rows_checked']==len(physical)==660
    csvout('independent_baselines.csv',baselineout);csvout('independent_scenarios.csv',out)
    csvout('independent_affected_journeys.csv',journeyout);csvout('independent_cash.csv',cashout)
    csvout('timebase_audit.csv',timeout);csvout('delay_template_conflicts.csv',conflicts)
    jsonout('recalculation_counts.json',dict(counts,baseline_groups=len(baselineout),overlay_combinations=len(out),
        affected_journey_rows=len(journeyout),component_rows_checked=len(published_components),timestamp_events=len(timeout),
        wrong_timestamp_events=sum(r['error_minutes']!=0 for r in timeout)))
    checked('CKR03','Eight programme/scenario baselines independently reconciled, without selector or pooled alternatives',8)
    checked('CKR04','40 economic overlays, 240 union journey rows, 660 capacity rows and all cost components independently matched',40)
    checked('CKR05','Cash events independently derived as direct cash flows and reconciled to stocks and accrual; fixture only',40)
    return out


def reference_joins():
    reference=j('reference_input_manifest.json')
    oldlegs=rows('inputs/tsiri_flights.csv');newlegs=rows('inputs/reference_set002/principal_calendar.csv')
    oldsales=rows('inputs/tsiri_sales.csv');newsales=rows('inputs/reference_set002/itinerary_sales.csv')
    out=[]
    def key(r):return tuple(r[k] for k in ['date','origin','destination','departure_utc_minute','arrival_utc_minute','block_minutes'])
    for old,new in [('H_UFA_8','H_UFA_8'),('H_UFA_4','H_UFA_4'),('D_case','D_previous_best8')]:
        a={r['id']:key(r) for r in oldlegs if r['profile']=='ROUTE_INPUTS_UPPER_100' and r['network']==old}
        z={r['id']:key(r) for r in newlegs if r['network']==new}
        assert collections.Counter(a.values())==collections.Counter(z.values())
        for sc in ['base','cautious']:
            left=[r for r in oldsales if r['profile']=='ROUTE_INPUTS_UPPER_100' and r['network']==old and r['scenario']==sc]
            right=[r for r in newsales if r['network']==new and r['scenario']==sc]
            def smap(ss,mm):return {(r['origin'],r['destination'],r['day'],tuple(mm[id] for id in r['flight_ids'].split(';'))):r for r in ss}
            aa,zz=smap(left,a),smap(right,z);assert len(aa)==len(left) and len(zz)==len(right) and set(aa)==set(zz)
            maximum=0
            for k in aa:
                for field in ['sold_journeys','gross_revenue','foregone_RW_revenue','new_pax_variable','saved_old_pax_variable']:
                    eq(aa[k][field],zz[k][field]);maximum=max(maximum,abs(float(aa[k][field])-float(zz[k][field])))
            out.append(dict(baseline_network=old,reference_network=new,scenario=sc,legs=len(a),itineraries=len(left),
                max_abs_delta=maximum,natural_key_join='PASS',baseline_replaced=False,
                calendar_semantic_acceptance='NOT_IMPLIED; both references retain absolute-minute grain'))
    csvout('reference_joins.csv',out)
    checked('CKR06','Pinned set002 natural-key equivalence checked; no baseline substitution, no budget-v2 pass inherited',6)


def adversarial_probes():
    o=frozen_module();d=j('scenario_definitions.json');origin=datetime.fromisoformat(d['period_start']).replace(tzinfo=UTC)
    legs,sales,caps,base=load_dataset('H_UFA_8','base')
    policies={p['id']:p for p in d['scenarios']};cancel=policies['cancel_pretravel_no_protection']
    result=[]
    def record(id,expectation,observed,status='PASS',scope='EXACT_FROZEN_CODE_PROBE'):
        result.append(dict(id=id,expectation=expectation,observed=observed,status=status,scope=scope))
    def rejected(id,fn):
        try:fn()
        except (ValueError,AssertionError) as err:record(id,'reject invalid or unsupported input',str(err));return
        raise AssertionError((id,'not rejected'))
    # Day1 cancellation remains a valid arithmetic stress despite the date bug.
    a,_,_,_=o.apply(legs,sales,caps,base,cancel,d)
    eq(a['overlay_delta_before_unknown_rub'],854454.44680853);eq(a['lost_net_revenue_rub'],6496147.739848063)
    record('DAY1_MONEY','16 cancelled, one union fare, no second migration loss',a)
    sample=next(r for r in sales if r['origin']=='ARH' and r['destination']=='MRV' and r['day']=='1')
    aa,zz=sample['flight_ids'].split(';')
    for subset in [{aa},{zz},{aa,zz}]:
        selected=o.lost_journeys([sample],subset);assert selected==[sample]
    eq(float(sample['fare_once'])*float(sample['sold_journeys']),501467.45034255)
    record('UNION_BOTH_LEGS','one lost fare with either or both legs cancelled',dict(journey=sample,one_fare=sample['gross_revenue']))
    narrow=copy.deepcopy(d);chosen=next(r for r in legs if r['id']==zz);t=at(chosen,'departure',origin)
    narrow['episode'].update(start_utc=t.isoformat(),end_utc_exclusive=(t+timedelta(minutes=1)).isoformat())
    na,nlegs,njourneys,_=o.apply(legs,sales,caps,base,cancel,narrow)
    assert na['template_rotation_status']=='UNRESOLVED_TEMPLATE_DISCONTINUITY'
    partially=[r for r in njourneys if int(r['linked_leg_count'])==2 and int(r['affected_leg_count'])==1]
    assert partially
    remaining_id=next(id for id in partially[0]['flight_ids'].split(';') if id!=chosen['id'])
    kept=next(r for r in nlegs if r['flight_id']==remaining_id);assert kept['action']=='unchanged' and kept['avoided_flight_cost_rub']==0
    record('ONE_OF_TWO_CANCELLED','whole itinerary lost; other physical flight cost retained; no invented protection',dict(summary=na,example=partially[0],remaining_flight=kept))
    ep=dict(d['episode'],start_utc=t.isoformat(),end_utc_exclusive=(t+timedelta(microseconds=1)).isoformat())
    assert o.hits(chosen,ep)
    ep=dict(d['episode'],start_utc=(t-timedelta(seconds=1)).isoformat(),end_utc_exclusive=t.isoformat());assert not o.hits(chosen,ep)
    record('HALF_OPEN_DAY1','inclusive start; exclusive end','PASS')
    ep=dict(d['episode'],start_utc=t.astimezone(timezone(timedelta(hours=5))).isoformat(),end_utc_exclusive=(t+timedelta(minutes=1)).astimezone(timezone(timedelta(hours=5))).isoformat())
    assert o.hits(chosen,ep);record('AWARE_TIMEZONE_EQUIVALENCE','same instant at UTC+05 and Z','PASS within day1; timebase defect is separate')
    zero=copy.deepcopy(d);zero['episode']['end_utc_exclusive']=zero['episode']['start_utc']
    zs,*_=o.apply(legs,sales,caps,base,cancel,zero);assert zs['affected_physical_legs']==0 and zs['overlay_delta_before_unknown_rub']==0
    record('ZERO_WINDOW','no affected legs and zero money delta','PASS')
    negative=dict(ep,end_utc_exclusive=(t-timedelta(minutes=1)).isoformat());rejected('NEGATIVE_WINDOW',lambda:o.hits(chosen,negative))
    # Overlapping event windows must be unioned before the itinerary lookup.
    union={r['id'] for r in legs if exposed(r,d['episode'],origin)}
    assert o.lost_journeys(sales,union|union)==o.lost_journeys(sales,union)
    record('OVERLAPPING_EPISODES_UNION','same cancellation set counted once','PASS as set union; no multi-episode API claimed')
    rejected('OVERBOOK',lambda:o.validate_capacity([{'flight_ids':legs[0]['id'],'sold_journeys':60}]*2,[legs[0]],{legs[0]['id']:100}))
    rejected('DUPLICATE_LINK',lambda:o.validate_capacity([{'flight_ids':legs[0]['id']+';'+legs[0]['id'],'sold_journeys':1}],[legs[0]],{legs[0]['id']:100}))
    rejected('UNKNOWN_LINK',lambda:o.validate_capacity([{'flight_ids':'absent','sold_journeys':1}],[legs[0]],{legs[0]['id']:100}))
    restored={**cancel,'old_migration_restored_fraction':1}
    rejected('NO_INVENTED_OLD_RW_RESTORATION',lambda:o.apply(legs,sales,caps,base,restored,d))
    fractions=copy.deepcopy(d);fractions['avoidability_profiles'][cancel['avoidability']]['crew']=1.1
    rejected('INVALID_AVOIDABILITY',lambda:o.apply(legs,sales,caps,base,cancel,fractions))
    for badminutes in [1,1440*8]:
        bad={**policies['delay_bank_next_day_fare_retained'],'delay_minutes':badminutes}
        rejected('DELAY_REJECT_'+str(badminutes),lambda:o.apply(legs,sales,caps,base,bad,d))
    # Independently reproduce the supplied concern from exact author add_leg.
    day2=[r for r in legs if r['day']=='2'];assert len(day2)==16
    wrong=[dict(id=r['id'],correct=at(r,'departure',origin).isoformat(),old=o.instant(r,'departure').isoformat(),
        error_minutes=(o.instant(r,'departure')-at(r,'departure',origin)).total_seconds()/60) for r in day2]
    assert all(r['error_minutes']==1440 for r in wrong)
    dec8=copy.deepcopy(d);dec8['episode'].update(start_utc='2026-12-08T00:00:00+00:00',end_utc_exclusive='2026-12-09T00:00:00+00:00')
    actual={r['id'] for r in legs if exposed(r,dec8['episode'],origin)};buggy={r['id'] for r in legs if o.hits(r,dec8['episode'])}
    assert len(actual)==16 and len(buggy)==0
    record('TIMEBASE_DAY2','16 true Dec8 legs must be selected',dict(old_selected=sorted(buggy),correct_selected=sorted(actual),day2_timestamps=wrong),'CONFIRMED_DEFECT')
    delayed,_,_,_=o.apply(legs,sales,caps,base,policies['delay_bank_next_day_fare_retained'],d)
    shifts={r['id']:1440 for r in legs if exposed(r,d['episode'],origin)}
    issues=template_issues(legs,origin,shifts)
    assert delayed['template_rotation_status']=='TEMPLATE_ONLY_CONTINUITY_PASS' and len(issues)==23
    record('TIMEBASE_DELAY_COLLISION','hold served-all branch when shifted day1 collides with original day2',dict(
        published_status=delayed['template_rotation_status'],correct_adjacent_conflicts=len(issues),labels=sorted({r['planning_label'] for r in issues})), 'CONFIRMED_DEFECT')
    # Cash alternatives: direct flows computed without the overlay cash bridge.
    saved={k:a['saved_'+k+'_rub'] for k in COMPONENTS+('new_pax_variable',)};loss=a['lost_net_revenue_rub'];timing=d['cash_timing_stress']
    prepaid,prepaidpeak=cash_direct(loss,saved,timing);spot,spotpeak=cash_direct(loss,saved,timing,fuel_cash_day=0)
    eq(prepaidpeak,6078104.30319147);eq(prepaid[-1]['cumulative_delta_cash_rub'],854454.44680853)
    eq(spot[-1]['cumulative_delta_cash_rub'],prepaid[-1]['cumulative_delta_cash_rub']);assert spotpeak==0
    nofuelreplenish=collections.defaultdict(float)
    nofuelreplenish[3]+=saved['new_pax_variable'];nofuelreplenish[7]-=loss
    record('FUEL_PREPAID_VS_PAY_ON_USE','same accrual, different cash trough; future procurement reduction is conditional',dict(
        inventory_already_bought=prepaid,inventory_peak=prepaidpeak,pay_on_use=spot,pay_on_use_peak=spotpeak,
        no_reduced_replenishment_by_horizon_terminal_cash=math.fsum(nofuelreplenish.values()),
        retained_inventory_at_horizon=saved['fuel_product']),scope='INDEPENDENT_CONTRACT_AND_CASH_COUNTERFACTUAL')
    usage=policies['cancel_usage_billed_sensitivity'];ua,*_=o.apply(legs,sales,caps,base,usage,d)
    extra=ua['overlay_delta_before_unknown_rub']-a['overlay_delta_before_unknown_rub'];eq(extra,1347012.8)
    retained=copy.deepcopy(d);retained['avoidability_profiles'][cancel['avoidability']]['fuel_product']=0;retained['avoidability_profiles'][cancel['avoidability']]['new_pax_variable']=0
    ra,*_=o.apply(legs,sales,caps,base,cancel,retained);eq(ra['overlay_delta_before_unknown_rub'],-loss)
    record('USAGE_BILLED_VS_RETAINED','only named avoidable charges; fixed crew retained; no right to call real cancellation beneficial',dict(
        named_extra_usage_savings_rub=extra,retained_all_costs_delta_rub=ra['overlay_delta_before_unknown_rub'],
        base_crew_retained_rub=a['crew_cost_retained_rub'],usage_crew_retained_rub=ua['crew_cost_retained_rub']),scope='CONDITIONAL_CONTRACT_COUNTERFACTUAL')
    # Event timing: terminal closed fixture is not the period-end delta or gross reserve.
    balance_day6=math.fsum(e['delta_cash_rub'] for e in prepaid if e['relative_day']<7)
    eq(balance_day6,saved['new_pax_variable'])
    record('CASH_PERIOD_END_VS_PEAK','weekly end precedes refund; day14 terminal and day7 peak differ',dict(
        period_start='2026-12-07',weekly_end_exclusive='2026-12-14',cash_delta_before_day7=balance_day6,
        cash_delta_after_day7=-prepaidpeak,terminal_after_day14=prepaid[-1]['cumulative_delta_cash_rub'],
        gross_company_cash_reserve=None,actual_intraday_payment_order=None),scope='INDEPENDENT_TIMING_INTERPRETATION')
    # Same-day net balances cannot identify an actual intraday peak.
    credit,debit=10.,10.
    record('SAME_DAY_ORDER_UNKNOWN','same daily terminal balance does not fix intraday funding',dict(
        daily_net=credit-debit,credit_first_peak=0,debit_first_peak=10,
        default_fixture_has_distinct_nonzero_cash_days=True),scope='GENERAL_BOUNDARY_COUNTEREXAMPLE_NOT_A_DEFECT_IN_PUBLISHED_DAYS_3_7_14')
    rejected('UNSUPPORTED_PRECOLLECTION',lambda:o.cash_events(loss,saved,0,'cancel',{**timing,'precollected_net_fare_fraction':.5}))
    ns,*_=o.apply(legs,sales,caps,base,policies['no_kover'],d)
    rs,*_=o.apply(legs,sales,caps,base,policies['restrictions_removed_other_risks_retained'],d)
    for k in ns:
        if k not in {'scenario_id'}:assert ns[k]==rs[k],k
    assert scenario_parameters('base')[0]['deicing_probability']>0 and d['episode']['probability'] is None and d['episode']['end_date_forecast'] is None
    record('REMOVAL_EQUALS_BASELINE','economic/physical baseline restored; deicing and unknown risks retained','PASS; baseline_id intentionally remains no_kover')
    # Matching monetary period is a necessary adapter condition; no budget/donor recomputation.
    record('STRATEGY_BOUNDARY','Delta_methods + delta_A - delta_B - (X_A-X_B)',dict(
        required_same_period=True,required_same_monetary_basis=True,donor_or_migration_second_deduction=False,
        actual_contract='UNKNOWN',full_profit='UNKNOWN'),scope='FORMULA_SCOPE_REVIEW_ONLY')
    jsonout('counterexamples.json',result)
    checked('CKR07','Independent adversarial probes executed, including two confirmed temporal failures',len(result))


def main():
    verify_inputs();verify_parameters();independent_overlays();reference_joins();adversarial_probes()
    jsonout('checks.json',dict(execution='COMPLETED',review_verdict='CHANGES',checks=CHECKS,
        confirmed_defects=['CKR-P2-TIMEBASE'],self_checks_inherited=False,budget_v2_acceptance_inherited=False,
        full_author_network_selector='NOT_RUN',source_acceptance='KHV selected rows only; UFA/OMS extraction inherited',
        market_dispatch_launch_acceptance='OUTSIDE_SCOPE',actual_RW_contracts='UNKNOWN'))
    jsonout('source_manifest.json',dict(review_delivery=DELIVERY,review_payload=PAYLOAD,root_base=BASE,
        sources=sorted(READS.values(),key=lambda r:(r['source_commit'],r['source_path'])),
        raw_sources='primary_raw_receipts.json; owner files read-only, never copied; no mutable peer outputs used',
        inherited_checks='none; upstream bytes and extracts are inputs, not acceptance'))
    print(json.dumps(dict(review='CHANGES',baseline_groups=8,overlay_combinations=40,checks=len(CHECKS),
        confirmed_defects=['CKR-P2-TIMEBASE'],actual_contracts='UNKNOWN')))


if __name__=='__main__':
    main()
