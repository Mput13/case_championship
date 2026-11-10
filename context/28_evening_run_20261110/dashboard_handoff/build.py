#!/usr/bin/env python3
"""Exact-blob serialization only. No solver, network, owner runtime or dependencies.

Run from any directory: python3 path/to/build.py [--verify]
--verify builds expected bytes in memory, compares all delivered bytes, and writes nothing.
CSV source_row uses a one-based logical CSV record including the header (first data row=2).
Text locators use one-based physical lines. JSON locators use RFC6901 pointers.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path(subprocess.check_output(['git', '-C', str(HERE), 'rev-parse', '--show-toplevel'], text=True).strip())
P = 'context/28_evening_run_20261110/'
AS_OF = '2026-11-10T20:50:14+03:00'
PINS = {
    'root': 'cb6b282260e7f3cb403e929e566512bc8a649045',
    'network': 'b47118a48b6d5480217077bf8699a63665c0eb7a',
    'network_review': 'cccc728b401d3a1234045220f42496ac48e0d475',
    'products': '388908b6da3539484cb8e2e03ada6ff5cb2204a4',
    'products_review': '6cc8c37e23c89488f3113efd96952d13f253f274',
    'evidence': '38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b',
    'evidence_review': '13f7c373954cc16b33a53b7c46436ee3f15f753b',
    'digital_growth': 'd48b4a4f86de29aa968665f1601b785bd1824c54',
    'digital_growth_review': '10464979fd510380aafe7e421d241a8f176d538d',
    'methods_dated': 'f99d6cd52dcc06995bf984fddd2f057226243b06',
    'dated_comparison_review': '994c6c0d293ae6053b4e73b279689c5020314e09',
    'methods_v4': '9f0b5d25af720107e99e209e1c69b098497358be',
    'strategy_synthesis_review': '934a32f87ad81adbb6808be3aa50d6072276e779',
    'methods_final': '5512f7d474a5db4bb658aae30b10f8b886629861',
}
ACTIVE = ['C01','C03','C04','C07','C10','C14','C17','C31','C33','C35']
SOURCE = {}
TABLES = {}
OUT = {}
CLAIMS = []

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def digest(b):
    return hashlib.sha256(b).hexdigest()

def js(o):
    return (json.dumps(o, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()

def out_json(path, obj):
    OUT[path] = js(obj)

def out_csv(path, rows, fields=None):
    if fields is None:
        fields = list(dict.fromkeys(k for r in rows for k in r))
    s = io.StringIO(newline='')
    w = csv.DictWriter(s, fieldnames=fields, lineterminator='\n', extrasaction='raise')
    w.writeheader()
    for r in rows:
        w.writerow({k: json.dumps(v, ensure_ascii=False, separators=(',', ':')) if isinstance(v,(dict,list)) else v for k,v in r.items()})
    OUT[path] = s.getvalue().encode()

def source(pack, path):
    sha = PINS[pack]
    key = sha + ':' + path
    if key not in SOURCE:
        b = git('show', key)
        SOURCE[key] = {'source_id': 'S' + hashlib.sha256(key.encode()).hexdigest()[:16],
                       'package': pack, 'commit': sha, 'path': path,
                       'git_blob': git('rev-parse', key).decode().strip(),
                       'sha256': digest(b), 'bytes': len(b),
                       'url': 'https://github.com/Mput13/case_championship/blob/' + sha + '/' + path,
                       'data': b}
    return SOURCE[key]

def ref(pack, path, row=None, line=None, pointer=None):
    s = source(pack,path)
    r = {k:s[k] for k in ['source_id','commit','path','git_blob','sha256','url']}
    if row is not None:
        r.update(locator_kind='csv_record_including_header', source_row=row)
    elif line is not None:
        r.update(locator_kind='text_line', source_line=line)
        r['url'] += '#L' + str(line)
    else:
        r.update(locator_kind='json_pointer' if pointer is not None else 'whole_blob', json_pointer=pointer or '')
    return r

def table(pack, path):
    key = (pack,path)
    if key not in TABLES:
        rows = list(csv.DictReader(io.StringIO(source(pack,path)['data'].decode('utf-8-sig'))))
        TABLES[key] = [dict(values=r, provenance=ref(pack,path,row=i+2)) for i,r in enumerate(rows)]
    return TABLES[key]

def txt(pack,path):
    return source(pack,path)['data'].decode('utf-8')

def line_ref(pack,path,needle):
    lines = txt(pack,path).splitlines()
    hits = [i+1 for i,l in enumerate(lines) if needle in l]
    if not hits:
        raise ValueError('Missing text locator: '+path+' :: '+needle)
    return ref(pack,path,line=hits[0])

def family_path(pack, filename):
    return P + pack + '/' + filename

def list_tree(pack, path):
    return git('ls-tree','-r','--name-only',PINS[pack],path).decode().splitlines()

def canon(a,b):
    return '-'.join(sorted([a,b])) if a and b else ''

def source_rows(pack,folder):
    result = {}
    for p in list_tree(pack,folder):
        if p.endswith('.csv'):
            result[Path(p).stem] = table(pack,p)
    return result

def claim(cid, text, refs, **kw):
    CLAIMS.append(dict(claim_id=cid, text=text, provenance=refs, **kw))

def source_link(r):
    where = ':CSV-record-' + str(r['source_row']) if 'source_row' in r else ':L'+str(r['source_line']) if 'source_line' in r else ''
    return '['+r['commit'][:10]+':'+r['path']+where+']('+r['url']+')'

def normalize():
    # No live refs: enumerate only explicit commit trees and serialize without recomputation.
    network = source_rows('network',P+'network/v2/outputs')
    products = source_rows('products',P+'products/outputs')
    evidence = {f:table('evidence',P+'evidence/'+f+'.csv') for f in [
        'pair_registry','pair_hypothesis_join','weekly_service_context','alternative_paths',
        'alternative_timing_examples','fare_observations','source_registry','decision_gaps',
        'dated_service_instances','dated_service_records','subsidy_route_matches','fleet_facts','fleet_delivery_gates']}
    strategy = source_rows('methods_v4',P+'methods/strategy')
    dated = table('methods_dated',P+'methods/runs/integer_year_v1/annual_comparison.csv')
    for pack, paths in {
        'root':['context/00_brief/case5_requirements.md','context/26_strategy_reset_20261110/requirements.csv',
                'context/26_strategy_reset_20261110/contract.md',P+'contract.md',P+'hypotheses.csv',
                P+'integration/digital_growth/cards.md',P+'integration/digital_growth/correction.json'],
        'network':[P+'network/HANDOFF.md',P+'network/v2/README.md',P+'network/v2/programs.json'],
        'products':[P+'products/handoff.md',P+'products/passport.md',P+'products/source_addendum.md',P+'products/budget_requirements.json'],
        'evidence':[P+'evidence/findings.md'],
        'digital_growth':[P+'digital_growth/passport.md'],
        'methods_dated':[P+'methods/dated_readout.md'],
        'methods_v4':[P+'methods/strategy.md'],
        'network_review':[P+'network_review/report.md',P+'network_review/handoff.json'],
        'products_review':[P+'products_review/report.md',P+'products_review/manifests/handoff.json'],
        'evidence_review':[P+'evidence_review/report.md',P+'evidence_review/handoff.json'],
        'digital_growth_review':[P+'digital_growth_review/report.md',P+'digital_growth_review/handoff.json'],
        'dated_comparison_review':[P+'dated_comparison_review/report.md',P+'dated_comparison_review/findings.json',P+'dated_comparison_review/handoff.json'],
        'strategy_synthesis_review':[P+'strategy_synthesis_review/report.md',P+'strategy_synthesis_review/findings.json',P+'strategy_synthesis_review/handoff.json'],
    }.items():
        for p in paths: source(pack,p)

    joins = evidence['pair_hypothesis_join']
    # Exact 85 original associations, including alternative-path roles, are retained.
    route_links = [dict(**r['values'],provenance=r['provenance']) for r in joins]
    out_csv('route_links.csv',route_links)
    route_context = []
    pair_hyp = {}
    for r in joins:
        v = r['values']
        pair_hyp.setdefault(v['route'],set()).add(v['hypothesis'])

    def context(kind,r,hyp,route,network='CONTEXT_ONLY'):
        v = r['values']
        carrier = v.get('carriers',v.get('carrier',v.get('named_carriers','')))
        row = dict(record_id='RC:'+kind+':'+hyp+':'+str(r['provenance']['source_row']),
                   record_type=kind,hypothesis_id=hyp,scenario='NOT_APPLICABLE',network=network,
                   variant='COMPETITIVE_CONTEXT_NOT_ACTION',route=route,
                   origin=v.get('origin',v.get('airport_a','')),destination=v.get('destination',v.get('airport_b','')),
                   date=v.get('date',v.get('leg1_date','')),
                   period_start=v.get('period_start',''),period_end=v.get('period_end',''),
                   time_class='PUBLISHED_2026_CONTEXT',carrier=carrier,
                   flight_number=v.get('flights',v.get('flight',v.get('leg1_flight',''))),aircraft=v.get('aircraft',''),
                   frequency_value=v.get('oneway_departures',''),frequency_unit=v.get('unit','NOT_CONFIRMED'),
                   price_value=v.get('advertised_from_rub',''),
                   price_unit='RUB advertised-from; year/baggage/net basis unconfirmed' if 'advertised_from_rub' in v else 'NOT_CONFIRMED',
                   coverage_status=v.get('coverage_status',v.get('air_market_status',v.get('status',v.get('classification','PARTIAL')))),
                   complete_market='False',provenance=r['provenance'],source_fields=v)
        if kind=='fare': row['time_class']='ADVERTISEMENT_CAPTURE_2026_TRAVEL_YEAR_UNCONFIRMED'
        if kind=='pair_coverage': row['time_class']='MIXED_EVIDENCE_COUNTS_NOT_A_SCHEDULE'
        if kind in ['alternative','alternative_timing']: row['time_class']='PUBLISHED_LEGS_DERIVED_ALTERNATIVE_NOT_NETWORK'
        route_context.append(row)

    for name,kind in [('pair_registry','pair_coverage'),('weekly_service_context','weekly_service_summary'),('dated_service_instances','published_departure'),('fare_observations','fare'),('decision_gaps','gap')]:
        for r in evidence[name]:
            for h in sorted(pair_hyp.get(r['values']['route'],set())):
                context(kind,r,h,r['values']['route'])
    for name,kind in [('alternative_paths','alternative'),('alternative_timing_examples','alternative_timing')]:
        for r in evidence[name]:
            v=r['values']; airports=v.get('path','').split('>')
            route=v.get('route',canon(airports[0],airports[-1]))
            context(kind,r,v['hypothesis'],route,v.get('network','ALTERNATIVE_CONTEXT_ONLY'))

    program=[]
    mapping={'KUF4':'C03','KUF4_SVX_deployed':'C03','OMS1':'C04','OMS4':'C04','OMS8':'C04','C01':'C01','C07':'C07','C33':'C33'}
    for kind,rows,pack in [('route_delta',network['route_deltas'],'network'),('dated_flight',network['dated_flights'],'network'),('dated_flight',products['dated_flights'],'products')]:
        for r in rows:
            v=r['values']; net=v['network']; hyp=v.get('hypothesis',mapping.get(net,''))
            assert hyp in ACTIVE,(kind,hyp,net)
            row=dict(record_id='PC:'+pack+':'+kind+':'+str(r['provenance']['source_row']),record_type=kind,
                     hypothesis_id=hyp,scenario=v.get('scenario','calendar_common'),network=net,
                     variant=v.get('variant',v.get('status','')),route=canon(v.get('origin'),v.get('destination')),
                     directed_route=v.get('origin','')+'-'+v.get('destination',''),
                     origin=v.get('origin',''),destination=v.get('destination',''),date=v.get('date',v.get('service_date','')),
                     flight_id=v.get('flight_id',''),flight_number=v.get('flight_number',''),
                     change=v.get('change',v.get('status',v.get('schedule_status',''))),
                     departure_before=v.get('departure_before',''),departure_after=v.get('departure_after',v.get('departure_local','')),
                     departure_utc=v.get('departure_utc',''),arrival_utc=v.get('arrival_utc',''),
                     aircraft=v.get('aircraft','Tu-214 194-seat scenario; actual tail UNKNOWN' if hyp=='C31' and ('TU' in v.get('tail_slot','').upper() or net in ['REPLACE_TU_MRV','KEEP_TU_TLV_CANCEL_IF_REPLACED']) else 'SSJ100/RRJ95 100-seat scenario analog; external feeder type not accepted'),
                     seats=v.get('seats',''),block_minutes=v.get('block_minutes',''),block_hours=v.get('block_hours',''),
                     fixture_pax=v.get('fixture_pax',''),fixture_pax_status=v.get('fixture_pax_status','NOT_A_SALES_OBSERVATION'),
                     time_class=('PUBLISHED_REFERENCE_2026' if v.get('schedule_status')=='PUBLISHED_REFERENCE' else 'DIAGNOSTIC_2026_PROXY_NOT_FUTURE_PUBLICATION') if pack=='network' else ('FUTURE_KEEP_SCENARIO_NOT_OBSERVED' if 'KEEP_SCENARIO' in v.get('status','') else 'PROPOSED_'+v.get('date','')[:4]),
                     summation='ALTERNATIVE_PROGRAMMES; filter network/variant/scenario before counting flights',
                     provenance=r['provenance'],source_fields=v)
            # Exact matching of route delta to dated flight; no floating/clock matching.
            matches=[x for x in network['dated_flights'] if pack=='network' and kind=='route_delta' and
                     all(x['values'].get(k)==v.get(k) for k in ['network','variant','flight_id'])]
            row['dated_flight_refs']=[x['provenance'] for x in matches]
            program.append(row)
    # Add an explicit source gap for calculation legs that are not in the evidence registry.
    existing={(r['hypothesis_id'],r['route']) for r in route_context if r['record_type']=='pair_coverage'}
    for r in program:
        key=(r['hypothesis_id'],r['route'])
        if key not in existing:
            context('calculation_pair_gap',dict(values={'route':r['route'],'origin':r['origin'],'destination':r['destination'],
                'coverage_status':'NOT_IN_EVIDENCE_PAIR_REGISTRY','next_gap':'No full competitor inference; exact physical/donor leg needs source coverage'},
                provenance=r['provenance']),r['hypothesis_id'],r['route'])
            # Distinguish IDs from the same source row number in other sources.
            route_context[-1]['record_id']='RC:calculation_pair_gap:'+r['record_id']
            existing.add(key)
    out_csv('program_changes.csv',program)
    out_json('program_changes.json',{'schema':1,'rows':program,'units':{'block_minutes':'minutes per flight','block_hours':'hours per flight','seats':'physical seats per flight','fixture_pax':'base capacity fixture, not observed sales'},'additivity':'No cross-network/variant sum; calendar_common is not a third economic scenario'})
    out_csv('route_context.csv',route_context)
    out_json('route_context.json',{'schema':1,'rows':route_context,'coverage':'45 pairs/85 links source registry; calculation-only donor gaps retained; complete market never inferred','count_boundary':'359 publications ->215 unique departures,144 duplicate publications,12 conflicts. Do not add those counts to departures.'})
    # Small, exact data exports support drilldown, not a second research corpus.
    for name in ['dated_service_instances','dated_service_records','subsidy_route_matches','fleet_facts','fleet_delivery_gates']:
        out_json('evidence/'+name+'.json',{'rows':evidence[name],'qualification':'Source observations/publications only; no future award/free fleet/full market acceptance'})
    # Coordinates only from a pinned source file. MOW is never coerced into an airport.
    airport_rows=table('products',P+'products/inputs/ourairports_ru.csv')
    wanted={r[k] for r in program for k in ['origin','destination']}
    wanted.update(r['values'][k] for r in strategy['option_routes'] for k in ['origin','destination'])
    coords=[]
    for code in sorted(wanted):
        found=[r for r in airport_rows if r['values']['iata_code']==code] if code!='MOW' else []
        if len(found)==1:
            v=found[0]['values']; coords.append(dict(code=code,name=v['name'],latitude=v['latitude_deg'],longitude=v['longitude_deg'],status='PINNED_AIRPORT_COORDINATES',provenance=found[0]['provenance']))
        else:coords.append(dict(code=code,name='Москва (агрегат; аэропорт не выбран)' if code=='MOW' else '',latitude='',longitude='',status='CITY_AGGREGATE_UNRESOLVED' if code=='MOW' else 'COORDINATES_NOT_PROJECTED',provenance=[]))
    out_csv('airports.csv',coords)
    return network,products,evidence,strategy,dated,program,route_context

def acceptance():
    final_rows=table('methods_final',P+'methods/final_acceptance.csv')
    for name in ['final_handoff.md','freeze.json','final_acceptance.csv']:
        OUT['methods_final/'+name]=source('methods_final',P+'methods/'+name)['data']
    definitions=[
        ('network','network_review','APPROVE_SCOPED','Conditional C01/C03/C04/C07/C33 diagnostic arithmetic/calendar and upper bounds; exact subject only','market/free tails/launch/year strategy/fullPnL/cash'),
        ('products','products_review','APPROVE_SCOPED','Conditional money/calendar/treasury fixtures/readiness truncation/own KEEP/support constraints','market/actual resource/contracts/award/full company budget/cash'),
        ('evidence','evidence_review','APPROVE_SCOPED','Exact source extraction and applicability conditions; OLD144 historical raw hash absent','market/economics/2027 award/free fleet/bookability/final20kg/inventory'),
        ('digital_growth','digital_growth_review','APPROVE_SCOPED','Anonymous observations and hypothetical threshold arithmetic; EV-DIGITAL-N01 separate correction','observed causal effect/AB/payment/refund/charter eligibility/company deliveries'),
        ('methods_dated','dated_comparison_review','APPROVE_SCOPED','96 dated annual cases/2298 weekly LP; same-flight retime; one C31 week/full C35 contract; H1-H11 retained','market/real fleet/award/fullPnL/cash/global hub impossibility/annual projection of retimed week'),
        ('methods_v4','strategy_synthesis_review','APPROVE_SCOPED','Exact v4 conditional card projections/24 finite options/144 aggregate readiness gates/mixed11/budget boundaries; freshEV-MR04, not inherited','market/physical fleet/launch permission/fullPnL/cash/future company rank/TEAM_ACCEPTED/global mixed optimum'),
        ('dashboard_handoff',None,'NOT_REVIEWED','This serializer checks references, identity, grains and units','independent assembly review; no subject calculation rerun'),
    ]
    rows=[]
    for pack,review,verdict,scope,excluded in definitions:
        p=P+(review or '')+'/report.md'
        rows.append(dict(package=pack,subject_sha=PINS.get(pack,'OUTER_COMMIT'),verdict=verdict,
                         review_sha=PINS.get(review,'') if review else '',as_of=AS_OF,accepted_scope=scope,not_accepted=excluded,
                         team_accepted='False',review_provenance=ref(review,p) if review else []))
    for r in final_rows:
        v=r['values'];match=next((x for x in rows if x['subject_sha']==v['subject_sha']),None)
        if match is None:
            match=dict(package=v['id'],subject_sha=v['subject_sha'],verdict=v['verdict'],review_sha=v['review_sha'],as_of=AS_OF,
                       accepted_scope='Prior exact scoped subject only; supplied authoritative final registry',not_accepted=v['scope_limits'],team_accepted=v['team_accepted'],review_provenance=[])
            rows.append(match)
        assert match['review_sha']==v['review_sha'] and match['verdict']==v['verdict']
        match['current_registry_provenance']=r['provenance']
        match['current_scope_limits']=v['scope_limits']
    out_csv('acceptance.csv',rows);out_json('acceptance.json',{'as_of':AS_OF,'rows':rows,'late_addendum':'Use a separate exact review receipt; never widen a prior subject verdict or rewrite this package.'})
    out_json('acceptance_events.json',{'as_of':AS_OF,'events':[
        {'event':'INPUT_AS_RECEIVED','subject_sha':PINS['methods_dated'],'qualification':'PENDING_EV_MR03','historical':True},
        {'event':'FRESH_EXACT_REVIEW_RECEIVED','subject_sha':PINS['methods_dated'],'review_sha':PINS['dated_comparison_review'],'qualification':'APPROVE_SCOPED','receipt':ref('dated_comparison_review',P+'dated_comparison_review/handoff.json'),'historical':False},
        {'event':'INPUT_AS_RECEIVED','subject_sha':PINS['methods_v4'],'qualification':'PENDING_EV_MR04','historical':True},
        {'event':'FRESH_EXACT_REVIEW_RECEIVED','subject_sha':PINS['methods_v4'],'review_sha':PINS['strategy_synthesis_review'],'qualification':'APPROVE_SCOPED','receipt':ref('strategy_synthesis_review',P+'strategy_synthesis_review/handoff.json'),'historical':False},
        {'event':'D03_MINIMAL_PROSE_CORRECTION','subject_sha':PINS['digital_growth'],'projection_sha':PINS['root'],'qualification':'COORDINATOR_CORRECTION; independent correction review NOT_RUN','receipt':ref('root',P+'integration/digital_growth/correction.json')}
        ,{'event':'FINAL_OWNER_WRAPPER_FROZEN','subject_sha':PINS['methods_final'],'qualification':'PACKAGING_ONLY; authoritative8subject-review registry; no new analytical verdict','receipt':ref('methods_final',P+'methods/freeze.json')}
    ],'rule':'Historical pending/source acceptance rows are preserved. Current exact reviews are separate events; neither verdict expands to market/fleet/award/fullPnL/cash/team decision.'})
    return {r['package']:r for r in rows}

def metrics_for(h,network,products):
    metrics=[]
    def take(rows,predicate,fields,period,basis):
        for r in rows:
            v=r['values']
            if predicate(v):
                variant={k:v[k] for k in ['network','program','phase','cohorts','year','occupied_state','local_loss_fraction_trunk','local_loss_fraction_south','fare_case','demand_layer','additional_mrv_paid_each_leg_probe','foregone_tu_old_mission_contribution_probe','K_probe','summer_people_each_leg_probe','turn_minutes'] if k in v}
                for field,unit in fields:
                    if field not in v or v[field]=='':continue
                    metrics.append(dict(metric=field,value=v[field],unit=unit,period=period,scenario=v.get('scenario','calendar_common'),variant=variant,accounting_boundary=basis,provenance=r['provenance']))
    zero=lambda v:float(v.get('K_probe','0'))==0
    if h=='C01':
        take(network['C01_synchronization'],lambda v:v['local_loss_fraction_south']=='0',[(x,'RUB/diagnostic 7 days') for x in ['delta_contribution_rub_week','contribution_sync_rub_week','Kmax_full_base_rub_week']]+[('new_through_journeys_week','one-way OD journeys/diagnostic 7 days'),('segments_week','passenger segments/diagnostic 7 days')],'2026-12-07/2026-12-13 diagnostic proxy','Sync delta and whole-programme contribution are separate; before excluded K/donor/other-network effects')
    if h in ['C03','C04']:
        take(network['fixed_programs'],lambda v:v['hypothesis']==h,[('contribution_rub_week','RUB/diagnostic 7 days'),('block_hours_week','block-hours/diagnostic 7 days'),('local_journeys_week','one-way OD journeys/diagnostic 7 days'),('ticket_revenue_rub_week','RUB/diagnostic 7 days')],'2026-12-07/2026-12-13 diagnostic proxy','Local-only contribution before K/alternative use/signed other network')
        take(network['bank_upper_bound'],lambda v:(v['network']=='KUF4')==(h=='C03'),[('ideal_bank_contribution_rub_week','RUB/diagnostic 7 days')],'2026-12-07/2026-12-13 diagnostic proxy','Ideal-bank upper bound at planning LF85/80, not a feasible timetable')
        if h=='C03':take(network['C03_base_comparison'],lambda v:True,[('Kmax_extra_KUF_base_minus_deployment_lodging_rub_week','RUB/diagnostic 7 days')],'2026-12-06/2026-12-13 deployment comparator','Difference between added base expense and deployment lodging; not total profit')
    if h=='C07':take(network['C07_extension'],lambda v:v['turn_minutes']=='45',[('delta_contribution_rub_week','RUB/diagnostic 7 days'),('extra_block_hours_week','block-hours/diagnostic 7 days'),('new_local_OMS_KJA_week','one-way OD journeys/diagnostic 7 days'),('new_through_SVX_KJA_week','one-way OD journeys/diagnostic 7 days')],'2026-12-08/2026-12-12 diagnostic proxy','Delta versus KEEP, before K_extension/lost next assignment/signed other network')
    if h=='C33':take(network['C33_retiming'],lambda v:v['local_loss_fraction_trunk']=='0.15',[('delta_contribution_rub_week','RUB/diagnostic 7 days'),('new_through_journeys_week','one-way OD journeys/diagnostic 7 days')],'2026-12-08/2026-12-12 diagnostic proxy','Separate occupied-state sensitivity; before overnight/retime/changed slot losses')
    if h=='C10':take(products['C10_contract_thresholds'],lambda v:zero(v) and v['cohorts']=='1',[('minimum_guarantee_return_per_person','RUB/person round-trip'),('minimum_guarantee_to_beat_ordinary_return_per_person','RUB/person round-trip'),('roundtrips','round trips/programme')],'launch1 2027-01-04/2027-02-01; steady one 28-day replacement cycle','Guaranteed contract price threshold; full K_block vs ordinary K difference are distinct')
    if h=='C14':take(products['C14_full_package_thresholds'],zero,[('minimum_air_guarantee_return_per_person','RUB/person round-trip'),('minimum_package_price_per_person','RUB/person full 14-night package'),('distinct_return_customers','distinct return customers/programme'),('peak_beds','simultaneous beds'),('block_hours','block-hours/programme')],'departures2027-11-01/2027-12-06; returns through2027-12-20','Whole programme threshold before K; hotel/airline participants separated in cash')
    if h=='C17':take(products['C17_seasonal_thresholds'],lambda v:zero(v) and v['summer_people_each_leg_probe']=='40',[('minimum_summer_paid_people_each_leg','paying passengers/summer one-way flight'),('winter_paid_segments','passenger segments/year winter dates'),('winter_variable_contribution','RUB/year winter dates'),('winter_roundtrips','round trips/year winter'),('summer_roundtrips','round trips/year summer')],'row year2027 or2028; fixed source seasonal calendar','Year threshold before K; no claim that unknown summer demand is zero')
    if h=='C31':
        seen=set()
        rows=[]
        for r in products['C31_replacement_frontier']:
            v=r['values']; key=v['scenario']
            if v['demand_layer']=='nastya_primary' and v['additional_mrv_paid_each_leg_probe']=='0' and v['foregone_tu_old_mission_contribution_probe']=='0' and key not in seen:rows.append(r);seen.add(key)
        take(rows,lambda v:True,[('maximum_tu_new_allin_cost_plus_K','RUB/one week; Tu all-in + lost TLV + K ceiling at L0 representation'),('additional_oms_paid_segments','new passenger segments/one week')],'2027-07-05/2027-07-11','No additional MRV sales; sum of Tu cost, lost old Tu mission and K must fit ceiling; other clean transfer H not evaluated')
    if h=='C35':
        take(products['C35_partner_thresholds'],zero,[('maximum_partner_price_per_reserved_seat','RUB/reserved seat-segment'),('through_oneway_journeys','one-way OD journeys/25-day contract'),('variable_incremental_contribution_at_block_probe','RUB/25-day contract after lost own contribution; before K')],'2027-07-06/2027-07-30','EXTERNAL alternative; all160 reserved seats paid; statistical incremental RW segments not accepted')
        take(products['addendum_C35_internal_KEEP'],zero,[('maximum_integration_retime_risk_K','RUB/25-day contract'),('through_oneway_journeys','one-way OD journeys/25-day contract')],'2027-07-06/2027-07-30','OWN KEEP alternative, one fare/two own seats/two pax costs; no additional subsidy; cannot sum with external')
    # Cash is explicitly marked as a participant-specific ledger/financing fixture.
    if h in ['C10','C14','C17','C31','C35']:
        take(products['cash_summary'],lambda v:v['hypothesis']==h,[('cash_balance_end','RUB participant cash at programme end'),('minimum_external_funding_if_same_day_netting','RUB participant minimum financing; daily netting lower bound')],'source programme dates; entity/kind in cash result rows','CASH_ONLY: entity/kind required; excluded cash terms unknown; not profit')
        # Retain participant and case labels alongside metric selection.
        for m in metrics:
            if m['accounting_boundary'].startswith('CASH_ONLY'):
                raw=next(r['values'] for r in products['cash_summary'] if r['provenance']==m['provenance'])
                m['variant'].update({k:raw[k] for k in ['entity','kind','comment']})
    return metrics

def cards(network,products,route_context,program,acceptance_rows,strategy):
    specs=json.loads((HERE/'card_specs.json').read_text())
    result=[]
    labels={'mechanism':'Механизм','before':'Было / KEEP','after':'Изменение','product':'Кто едет',
            'routes_frequency_period':'Пары, частоты и период','aircraft_resource':'Тип и рабочий ресурс',
            'resource_origin_and_old_mission':'Откуда самолёт и прежнее задание','competition_example':'Конкуренты и альтернативы',
            'result_reading':'Результат и его граница','excluded_costs_threshold':'Неучтённые расходы и порог',
            'cash':'Денежные потоки','continue_if':'Условие продолжения','stop_or_revisit_if':'Отказ и пересмотр'}
    md=['# Карточки десяти гипотез','',
        'As of '+AS_OF+'. Это условные расчётные опыты; решение команды о сети и запуске не принято. Числа ниже сохраняют исходные периоды и не образуют общего рейтинга. 25 резервных гипотез не отклонены экономически.','']
    for h in ACTIVE:
        s=specs[h];pack='network' if h in ['C01','C03','C04','C07','C33'] else 'products'
        entry=P+'network/v2/README.md' if pack=='network' else P+'products/handoff.md'
        owner_ref=line_ref(pack,entry,'## '+h+':') if pack=='network' else line_ref(pack,P+'products/passport.md','**'+h+',') if h in ['C10','C14','C17','C31','C35'] else ref(pack,entry)
        review_path=P+('network_review/report.md' if pack=='network' else 'products_review/report.md')
        review_heading='## C03/C04:' if h in ['C03','C04'] else '## '+h+':'
        review_ref=line_ref(pack+'_review',review_path,review_heading)
        metric=metrics_for(h,network,products)
        related_context=[r['record_id'] for r in route_context if r['hypothesis_id']==h]
        related_changes=[r['record_id'] for r in program if r['hypothesis_id']==h]
        sources=[owner_ref,review_ref]
        table_rows={}
        for name in s['tables']:
            rs=(network if pack=='network' else products).get(name,[])
            table_rows[name]=[r for r in rs if r['values'].get('hypothesis',r['values'].get('id',h))==h or name in ['bank_upper_bound','bank_exclusions','fixed_routes']]
        synthesis=[r for r in strategy['hypothesis_decisions'] if r['values']['id']==h]
        card=dict(hypothesis_id=h,**s,layer='PROPOSED_PROGRAMME_NOT_CITY_SCREENING_NOT_TEAM_DECISION',
                  economic_status=s['status'],market_status='NOT_ESTABLISHED',resource_status='HOLD' if h=='C31' else 'NOT_ESTABLISHED',
                  future_award_status='UNKNOWN',full_pnl_status='UNKNOWN',team_accepted=False,
                  metrics=metric,source_tables=table_rows,route_context_ids=related_context,program_change_ids=related_changes,
                  source_refs=sources,independent_scope=acceptance_rows[pack],
                  v4_decision={'qualification':'APPROVE_SCOPED_EV_MR04; exact9f0 only; not TEAM_ACCEPTED', 'review_sha':PINS['strategy_synthesis_review'], 'rows':synthesis})
        result.append(card)
        md += ['## '+h+' — '+s['title'],'',s['status']+'.','']
        for k,label in labels.items():
            md += ['**'+label+'.** '+s[k],'']
            extra=[]
            if k=='cash' and pack=='products':
                extra=[line_ref('products_review',review_path,'## Cash и readiness')]
            claim(h+'.'+k,s[k],[owner_ref,review_ref]+extra,hypothesis_id=h,qualification=acceptance_rows[pack]['verdict']+' arithmetic/mechanism only; launch not accepted')
        md += ['| Показатель | Сценарий / вариант | Точное значение | Единица | Период | Источник |',
               '|---|---|---:|---|---|---|']
        for i,m in enumerate(metric):
            if m['accounting_boundary'].startswith('CASH_ONLY'):continue
            var=', '.join(k+'='+v for k,v in m['variant'].items())
            md.append('| '+m['metric']+' | '+m['scenario']+'; '+var+' | '+m['value']+' | '+m['unit']+' | '+m['period']+' | '+source_link(m['provenance'])+' |')
            claim(h+'.metric.'+str(i+1),m['metric']+' = '+m['value'],[m['provenance']],hypothesis_id=h,unit=m['unit'],period=m['period'],scenario=m['scenario'],variant=m['variant'],accounting_boundary=m['accounting_boundary'])
        md += ['', '**Независимая проверка.** '+acceptance_rows[pack]['accepted_scope']+'. Не приняты: '+acceptance_rows[pack]['not_accepted']+'. '+source_link(review_ref)+'.',
               '', 'Связи: `route_context_ids` и `program_change_ids` в cards.json; исходные строки и варианты в `source_tables`. У каждой строки — exact SHA/file/record, без обращения к живой ветке.','']
    out_json('cards.json',{'schema':1,'as_of':AS_OF,'cards':result,'card_count':10,'team_decision':'NOT_ACCEPTED','additivity':'No single ranking or sum across periods, accounting boundaries, shared markets or resource alternatives'})
    OUT['cards.md']='\n'.join(md).encode()
    return result

def strategy_exports(strategy,dated):
    for name,rows in strategy.items():
        qualification='APPROVE_SCOPED_EV_MR04 exact9f0/review934a; arithmetic/meaning only; not TEAM_ACCEPTED'
        periods={
            'finite_options':'AUTHOR_52_48_CONCENTRATED model year; not dated2027/2028',
            'option_routes':'author fixed weekly52/48; not dated flights',
            'finite_option_readiness':'row year2027/2028; row delivery branch; aggregate resource only',
            'hypothesis_decisions':'source period field; heterogeneous programmes, never one score',
            'mixed11_budget':'2026-12-07/2026-12-13 diagnostic proxy; no annual projection',
            'mixed11_routes':'2026-12-07/2026-12-13 diagnostic proxy',
            'whole_company_bridge':'row case2028 plus historical2025 scale only',
            'budget_components':'accounting boundary/contract programme, not an observed cash period',
            'hypothesis_queue35':'as-of hypothesis history; no economic aggregation',
            'acceptance_register':'historical owner registry, current receipt in acceptance_events.json'}
        units={
            'finite_options':'annual_contribution_source=RUB/modelyear; annual_journeys_source=one-wayODjourneys/modelyear; annual_segments_source=passengersegments/modelyear; block_hours_week=blockhours/week; flights_week=directeddepartures/week; tails=count',
            'option_routes':'frequency_each_direction_week=directeddepartures/week; rows at program-leg grain; aggregate origin/destination to count unique pairs',
            'finite_option_readiness':'required_working_tails=constructedslots; days_with_aggregate_resource=calendardays; first/last=dates',
            'hypothesis_decisions':'unit preserved in source unit field; base_value/cautious_value use it',
            'mixed11_budget':'contribution/corrections/credit=RUB/diagnosticweek; sales=onewayODjourneys/diagnosticweek; flights=directeddepartures; blockhours=hours; slots=count',
            'mixed11_routes':'journeys=onewayODjourneys/diagnosticweek; frequency=directeddepartures/week; contribution_correction=RUB/diagnosticweek',
            'whole_company_bridge':'passengersegments/year; historical2025 != forecast2028',
            'budget_components':'no numeric value invented; required_source/actual_value preserved',
            'hypothesis_queue35':'categorical disposition;25reserve not rejection',
            'acceptance_register':'categorical exactsubject verdict; historical receipt never widened'}
        records=[dict(**r['values'],source_provenance=r['provenance'],handoff_period=periods.get(name,'source row period'),handoff_units=units.get(name,'source columns'),handoff_qualification=qualification,as_of=AS_OF) for r in rows]
        out_csv('strategy/'+name+'.csv',records)
        out_json('strategy/'+name+'.json',{'rows':records,'qualification':qualification,'units_and_periods':'Preserved row fields; annual_contribution_source is author model year (52/48 concentrated), not dated annual fullPnL; readiness days are aggregate resource gates; mixed11 is a local-only week'})
    out_json('dated_annual.json',{'rows':dated,'subject_sha':PINS['methods_dated'],'review_sha':PINS['dated_comparison_review'],'verdict':'APPROVE_SCOPED','qualification':'96 conditional dated annual cases; owner-shadow support remains shadow; no fullPnL/cash/market/real fleet acceptance. Not the v4 synthesis verdict.'})
    # Explicit periods/units not present as a numeric score or a hidden unit assumption.
    out_json('data_dictionary.json',{
        'source_row':'One-based logical CSV record including header; first data record2, not physical line for multiline CSV.',
        'empty':'Empty source numeric field means not supplied; never convert to zero.',
        'layers':{'city_screening':'Existing owner city scores/weights remain unchanged. A city score is not a programme result.',
                  'proposed_programmes':'Ten scoped calculations and exact source tables.',
                  'finite_options':'24 owner-synthesis options/205 route rows in v4, scopedEV-MR04exact934a; author-concentrated model calendar; not team decision.',
                  'dated_comparison':'f99 dated conditional arithmetic independently checked by994c; exact separate subject.',
                  'team_decision':'NOT_ACCEPTED: city/network/scenario/resources/budget still require decision.'},
        'program_changes_key':['record_type','hypothesis_id','scenario','network','variant','route','date','flight_id'],
        'route_context_key':['record_type','hypothesis_id','network','route','provenance.commit','provenance.path','provenance.source_row'],
        'join_rules':['cards.hypothesis_id -> program_changes.hypothesis_id and route_context.hypothesis_id',
                      'route_links retains each source network/role separately; alternatives are context, never ACTION flights',
                      'route_delta.dated_flight_refs matches exact network/variant/flight_id; base/cautious share calendar_common, do not count it twice',
                      'strategy.option_routes.option -> finite_options.option; finite_option_readiness.option -> finite_options.option',
                      'MOW is an unresolved city aggregate. Do not map to DME/SVO or draw a physical flight without a decision.'],
        'units':{'journey':'One directional endpoint trip; transfer consumes two flight seats and one fare.',
                 'segment':'One passenger on one flight leg; not interchangeable with journeys or unique people.',
                 'RT':'Round trip;2 directed departures per operated route; no blanket annual multiplication.',
                 'annual_contribution_source':'RUB per author model year, source_calendar AUTHOR_52_48_CONCENTRATED; not dated year fullPnL.',
                 'annual_journeys_source':'Expected one-way OD journeys per author model year.',
                 'annual_segments_source':'Passenger segments per author model year.',
                 'days_with_aggregate_resource':'Calendar days of row year/branch satisfying aggregate working slots; not physical operational approval.',
                 'mixed11_budget':'RUB/diagnostic7days, local-only no support; KUF–OMS pooled frequency4 each direction;3 constructed slots, no physical fleet approval.',
                 'whole_company_bridge':'Passenger segments/year2028 conditional plus historical2025 scale; future KEEP/market/rank unknown.',
                 'cash':'RUB by participant and payment dates; daily same-day netting is a financing lower bound, not profit or intraday solvency.'},
        'known_incompatibilities':['C07 andC33 shareWZ5071/5072', 'C33/KUF4/OMS4/OMS8 shareKUF–OMS endpoint demand',
                                 'C35external andown-feed share endpoint journeys/seats; never sum independently',
                                 'C31newOMSMon/Thu5/8July has no same-dateC35Tue/Fri feed',
                                 'OMS1/4/8, KUF4, ideal-bank and physical100 sensitivity are different constructions'],
        'q4_rule':'q4=q2*(1+exp(-2/k)) applies only to the open noncapped capture branch used here; do not apply mechanically under capacity caps or competitive capture.',
        'H11':'Current N(t) are consistent across27Dec2027–2Jan2028. New Jan1 deliveries require a common weekly programme before annual split; do not pick two programmes for one cross-year week.',
        'coordinates':'Only exact products388908 inputs/ourairports_ru.csv; MOW never resolved by substitution.'})

def appendices():
    rows=[]
    for p in list_tree('digital_growth',P+'digital_growth/illustrations'):
        if not p.endswith('.png'):continue
        s=source('digital_growth',p);name=Path(p).name;dest='appendices/'+name
        OUT[dest]=s['data']
        ident=name[:3]
        rows.append(dict(id=ident,filename=name,local_path=dest,source_path=p,source_sha=PINS['digital_growth'],sha256=s['sha256'],source_provenance=ref('digital_growth',p),purpose='Separate digital/№2 passport appendix; not main network',qualification='APPROVE_SCOPED originald48; D03 prose uses rootcb6 correction; charter eligibilityUNKNOWN'))
    assert len(rows)==14
    out_csv('appendix_index.csv',rows)
    out_json('appendix_index.json',{'images':rows,'passport_ref':ref('digital_growth',P+'digital_growth/passport.md'),
                                    'corrected_prose_ref':ref('root',P+'integration/digital_growth/cards.md'),
                                    'correction_receipt':ref('root',P+'integration/digital_growth/correction.json'),
                                    'digital_numbers':'Preserved; not recomputed or added to network.',
                                    'D03':'Removed unconfirmed «регулярный»; charter eligibility UNKNOWN; correction independent review NOT_RUN, original scoped review retained.'})
    OUT['appendix_index.md']=('\n'.join(['# Отдельные иллюстрации для паспорта','','14 PNG скопированы побайтно из exact d48b4a4f. Это приложение к паспорту, без перестройки основной сети. Числа не менялись. D03 читать с root-correction cb6b282; charter eligibility UNKNOWN.','']+['- ['+r['filename']+']('+r['local_path']+') — `'+r['source_sha']+':'+r['source_path']+'`' for r in rows])+'\n').encode()

def coverage():
    reqs=table('root','context/26_strategy_reset_20261110/requirements.csv')
    # Covers the deliverable requirement, not just successful serialization of an input.
    mapping={
        'R01':('условно','README.md; strategy/finite_options.csv','Существующий city-screening не пересчитан; полный longlist/top3/устойчивость не включены в exact текущую поставку.'),
        'R02':('условно','route_context.csv; evidence/fleet_facts.json','Есть частичный датированный контекст пар; полный разбор≥2региональныхбаз и переносимость/SVXистория не собраны здесь заново.'),
        'R03':('условно','dated_annual.json; strategy/finite_options.csv; acceptance.csv','Условная арифметика f99 и синтез v4 проверены отдельными exact reviews. Нет принятой общей стратегии/рынка/физического ресурса/fullPnL.'),
        'R04':('условно','strategy/option_routes.csv; strategy/mixed11_routes.csv; program_changes.csv','Есть варианты8–12,нет TEAM_ACCEPTED сети;MOWнеразрешён,банка/слоты/хвостыусловны.'),
        'R05':('условно','cards.json; route_context.csv; source_index.csv','Метод/единицы/периоды есть;наблюдаемыйOD/netyield2027–2028и полный конкурентный рынок отсутствуют.'),
        'R06':('условно','strategy/finite_option_readiness.csv; cards.json','Ветви/ресурсныеgates есть;N(t)сценарный,нет фактических передачRW/ввода/хвостов.'),
        'R07':('условно','cards.md; evidence/fleet_facts.json','SSJаналог/SJ100разделены;реальнаястоимость/нагрузкаSJ100/ПД-8неподтверждена.'),
        'R08':('условно','program_changes.csv; cards.json','KEEP/доноры/retimeназваны;остаткипродаж,tailassignmentи signedother-networkUNKNOWN.'),
        'R09':('условно','data_dictionary.json; strategy/mixed11_budget.csv','Исходныеscopedопытыиmixed11общийKUF–OMSсохранены;нетполногообщегоallocatorвсех10программ.'),
        'R10':('условно','route_context.csv; evidence/subsidy_route_matches.json; cards.md','Listing/правила/порогиесть;будущийaward/rate/netyield/реакцияконкурентовUNKNOWN.'),
        'R11':('условно','strategy/budget_components.csv; cards.json','ГраницыK/cashучастникиесть;реальныйполныйPnL/grosscash/KEEPsettlementнерассчитаны.'),
        'R12':('условно','dated_annual.json; strategy/whole_company_bridge.csv','Естьусловныйкалендарь;чистыйcompanyэффект/будущийKEEP/совместимыйрынок2028неизвестны,долянепринята.'),
        'R13':('не выполнено','passport_excerpt.md','Полнаяпринятаядорожнаякарта:ответственные/сроки/договоры/операционныйдопускдо2028за root/team.'),
        'R14':('готово','cards.json; strategy/hypothesis_queue35.csv','10условныхопытовпереданы,25резервныхсисторией;это выполнение scopedсборки,не запуск/экономическийотказ25.'),
        'R15':('условно','appendix_index.md; appendix_index.json','Анонимныйпуть/порогипроверены;AB/оплата/наблюдаемыйэффектNOT_RUN.'),
        'R16':('условно','appendix_index.md; appendix_index.json','Действующиеуслуги/изменения/порогисохранены;causalityиединаямаржазаказаUNKNOWN.'),
        'R17':('условно','appendix_index.json','D03исправленныйprose,порогитруда;chartereligibilityUNKNOWN,реальныйrefund/cashsavingNOT_RUN.'),
        'R18':('условно','strategy/whole_company_bridge.csv; appendix_index.md','Историческиймасштаб2025,цельбезсрока;нетдоказательствадостижения№2этойсетью/к2028.'),
        'R19':('готово','source_index.csv; acceptance.csv; source_manifest.json','Exactверсиииавторстворазделены;нетнаследованияreviewмеждуsubject.'),
        'R20':('условно','README.md','Координаторпередалexactвходы;сборщикнеимпортировалживыеветкиине поллилдругиезадачи.Журналпроверокколлегза root.'),
        'R21':('условно','HANDOFF.md','Ownbranchcommit/pushиremoteSHAподтверждаютсяфинальнымhandoffвне self-referentialmanifest.'),
        'R22':('готово','passport_excerpt.md; claim_pointers.csv','Безопасныетезисы/методпроверки/пробелывпакете;финальнаяприёмкаработызаroot.'),
        'R23':('готово','README.md; cards.json; appendix_index.md','Совместимыеданныеи14PNGпереданы.UI/Siteне менялись;встраиваниевдашбордNOT_RUN.'),
        'R24':('условно','requirements_coverage.csv; HANDOFF.md','Самостоятельнаяпроверкасборкиесть,независимыйreviewсборкизаroot;22:00непродлевается.')}
    readable_gaps={
        'R01':'City-screening не пересчитан. Полный longlist/top3 и проверка устойчивости не включены в текущие exact входы сборки.',
        'R02':'Есть частичный датированный контекст пар. Полный разбор минимум двух региональных баз, переносимости опыта и истории SVX здесь не собран заново.',
        'R03':'Условная арифметика f99 и синтез v4 имеют отдельные scoped reviews. Нет принятой общей стратегии, рынка, физического ресурса и fullPnL.',
        'R04':'Есть варианты 8–12 пар, нет TEAM_ACCEPTED сети. MOW не разрешён; банка, слоты и физические хвосты условны.',
        'R05':'Методы, единицы и периоды переданы. Наблюдаемый OD/net yield 2027–2028 и полный конкурентный рынок отсутствуют.',
        'R06':'Ветви поставок и resource gates переданы; N(t) сценарный. Нет подтверждённых передач RW, ввода и хвостов.',
        'R07':'SSJ-аналог и SJ100 разделены; реальные стоимость, нагрузка и ограничения SJ100/ПД-8 не подтверждены.',
        'R08':'KEEP, доноры и retime названы; остатки продаж, tail assignment и signed other-network UNKNOWN.',
        'R09':'Scoped опыты и общий KUF–OMS в mixed11 сохранены. Нет полного общего allocator всех десяти программ.',
        'R10':'Listing, правила и пороги сохранены; будущие award/rate/net yield и реакция конкурентов UNKNOWN.',
        'R11':'Переданы границы K и отдельные cash-участники. Реальные полный PnL, gross cash и KEEP settlement не рассчитаны.',
        'R12':'Есть условный датированный календарь. Чистый company эффект, будущий KEEP и совместимый рынок 2028 неизвестны; доля не принята.',
        'R13':'Полная принятая дорожная карта с ответственными, сроками, договорами и операционным допуском до 2028 остаётся за root/team.',
        'R14':'Десять условных опытов переданы, 25 резервных сохранены с историей. Это выполненная scoped сборка, а не запуск и не экономический отказ резервным.',
        'R15':'Анонимный путь и диагностические пороги проверены; AB, оплата и наблюдаемый эффект NOT_RUN.',
        'R16':'Существующие услуги, изменения и пороги сохранены. Причинный эффект и единая маржа заказа UNKNOWN.',
        'R17':'D03 использует исправленный prose; charter eligibility UNKNOWN. Реальный refund и cash saving NOT_RUN.',
        'R18':'Передан исторический масштаб 2025 и цель без срока. Достижение №2 этой сетью или к 2028 не доказано.',
        'R19':'Exact версии, авторство и subjects review разделены. Текущие receipts не переписывают исторические PENDING.',
        'R20':'Координатор передал exact входы. Сборщик не импортировал живые ветки и не поллил задачи; общий журнал проверки коллег остаётся у root.',
        'R21':'Own branch commit, push и remote SHA подтверждаются финальным handoff вне самоссылочного manifest.',
        'R22':'Безопасные тезисы, проверка сборки и пробелы переданы. Финальная приёмка кейса остаётся за root.',
        'R23':'Совместимые данные и 14 PNG переданы. UI/Site не менялись; фактическое встраивание в дашборд NOT_RUN.',
        'R24':'Личная проверка сериализации выполнена; независимый review сборки запускает root. Общий срок 22:00 не продлевается.'}
    rows=[]
    for r in reqs:
        v=r['values'];status,artifact,gap=mapping[v['id']]
        rows.append(dict(requirement_id=v['id'],question=v['question'],status=status,artifact=artifact,exact_gap=readable_gaps[v['id']],
                         scope='This immutable data handoff, not final case acceptance',provenance=r['provenance']))
    out_csv('requirements_coverage.csv',rows)
    OUT['requirements_coverage.md']=('\n'.join(['# Покрытие требований','','Статус относится к названной части результата, а не к готовности запуска.','', '| ID | Статус | Артефакт | Точный пробел / граница |','|---|---|---|---|']+['| '+r['requirement_id']+' | '+r['status']+' | '+r['artifact']+' | '+r['exact_gap']+' |' for r in rows])+'\n').encode()

def verify_structure(cards_,program,context,strategy,evidence):
    checks=[]
    def check(name,condition):
        if not condition: raise AssertionError(name)
        checks.append(name)
    check('exact ten distinct IDs', [c['hypothesis_id'] for c in cards_]==ACTIVE)
    check('network146/products402/deltas268 preserved',len(program)==816)
    check('45 evidence pairs',len(evidence['pair_registry'])==45)
    check('85 evidence links',len(evidence['pair_hypothesis_join'])==85)
    check('22 gaps not absence',sum(r['values']['coverage_status']=='GAP_NOT_ABSENCE' for r in evidence['pair_registry'])==22)
    check('359 publications preserved',len(evidence['dated_service_records'])==359)
    check('215 departures preserved',len(evidence['dated_service_instances'])==215)
    check('144 duplicate publications not frequency',len(evidence['dated_service_records'])-len(evidence['dated_service_instances'])==144)
    check('12 published conflicts retained',sum(r['values']['clock_or_type_conflict']=='True' for r in evidence['dated_service_instances'])==12)
    check('268 exact delta-to-flight links',all(len(r['dated_flight_refs'])==1 for r in program if r['record_type']=='route_delta'))
    airport_output=list(csv.DictReader(io.StringIO(OUT['airports.csv'].decode())))
    check('MOW coordinates never substituted',all(r['latitude']=='' and r['longitude']=='' and r['status']=='CITY_AGGREGATE_UNRESOLVED' for r in airport_output if r['code']=='MOW'))
    check('published departures have one exact date',all(re.fullmatch(r'2026-\d\d-\d\d',r['date']) for r in context if r['record_type']=='published_departure'))
    for name,rows,key in [('program',program,lambda r:tuple(r[x] for x in ['record_type','hypothesis_id','scenario','network','variant','route','date','flight_id'])),
                          ('context',context,lambda r:(r['record_type'],r['hypothesis_id'],r['network'],r['route'],r['provenance']['commit'],r['provenance']['path'],r['provenance'].get('source_row')))]:
        keys=[key(r) for r in rows]
        check(name+' unique declared grain',len(keys)==len(set(keys)))
        ids=[r['record_id'] for r in rows];check(name+' unique record IDs',len(ids)==len(set(ids)))
    options={r['values']['option'] for r in strategy['finite_options']}
    check('24 distinct finite options',len(options)==24)
    check('205 option route rows',len(strategy['option_routes'])==205)
    check('144 readiness rows',len(strategy['finite_option_readiness'])==144)
    for name in ['option_routes','finite_option_readiness']:
        check(name+' option FK',all(r['values']['option'] in options for r in strategy[name]))
    for option in options:
        routes=[r['values'] for r in strategy['option_routes'] if r['values']['option']==option]
        pairs={canon(r['origin'],r['destination']) for r in routes}
        stated=next(r['values']['model_endpoint_pairs'] for r in strategy['finite_options'] if r['values']['option']==option)
        check('program legs aggregated to pairs '+option,len(pairs)==int(stated))
    readiness_keys=[(r['values']['option'],r['values']['branch'],r['values']['year']) for r in strategy['finite_option_readiness']]
    check('readiness unique option/branch/year',len(readiness_keys)==len(set(readiness_keys)))
    queue=strategy['hypothesis_queue35'];check('queue35 preserved',len(queue)==35 and len({r['values']['id'] for r in queue})==35)
    check('25 reserve not rejection',sum(r['values']['id'] not in ACTIVE for r in queue)==25 and all(r['values']['not_rejected_for_nonselection']=='True' for r in queue))
    for c in cards_:
        check(c['hypothesis_id']+' has base/cautious',{'base','cautious'} <= {m['scenario'] for m in c['metrics']})
        check(c['hypothesis_id']+' metric units/period/boundary',all(m['unit'] and m['period'] and m['accounting_boundary'] for m in c['metrics']))
        check(c['hypothesis_id']+' separate cash semantics',all(('CASH_ONLY' in m['accounting_boundary'])==('cash' in m['metric'] or 'funding' in m['metric']) for m in c['metrics']))
    check('C35 statistical company growth excluded',all(m['metric']!='incremental_rw_passenger_segments' for c in cards_ for m in c['metrics']))
    # Every provenance pointer is checked against an exact existing blob and row/line.
    pointers=0
    def walk(o):
        nonlocal pointers
        if isinstance(o,dict):
            if {'commit','path','git_blob','sha256','source_id'} <= set(o):
                key=o['commit']+':'+o['path'];check('provenance source '+str(pointers),key in SOURCE)
                s=SOURCE[key];check('provenance blob/hash '+str(pointers),s['git_blob']==o['git_blob'] and s['sha256']==o['sha256'])
                if 'source_row' in o:
                    n=len(list(csv.DictReader(io.StringIO(s['data'].decode('utf-8-sig')))))
                    check('CSV locator '+str(pointers),2<=o['source_row']<=n+1)
                if 'source_line' in o:check('text locator '+str(pointers),1<=o['source_line']<=len(s['data'].decode().splitlines()))
                pointers+=1
            for v in o.values():walk(v)
        elif isinstance(o,list):
            for v in o:walk(v)
    walk(cards_);walk(program);walk(context);walk(strategy)
    out_json('verification.json',{'status':'PASS_SERIALIZATION_ONLY','as_of':AS_OF,'checks':len(checks),'provenance_pointers_checked':pointers,
                                  'counts':{'cards':10,'program_changes':len(program),'route_context':len(context),'finite_options':24,'option_routes':205,'readiness':144,'queue':35,'reserve':25,'png':14},
                                  'checked':['exact commit/blob/SHA256/bytes','CSV record/text line pointer ranges','declared primary grains and foreign keys','ten IDs/base/cautious/units/accounting boundaries','cash vs contribution metrics','MOW not resolved','unchanged PNG bytes'],
                                  'NOT_RUN':['owner models/allocator/economic recalculation','new research/network fetch/browser/UI QA','independent review of this assembly','market/resource/award/fullPnL acceptance']})

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--verify',action='store_true');args=ap.parse_args()
    network,products,evidence,strategy,dated,program,context=normalize()
    acc=acceptance()
    result=cards(network,products,context,program,acc,strategy)
    strategy_exports(strategy,dated);appendices();coverage()
    # Static, readable handoff texts are authored inputs of the serializer.
    for name in ['README.md','passport_excerpt.md','HANDOFF.md']:
        OUT[name]=(HERE/name).read_bytes()
    out_json('claim_pointers.json',{'claims':CLAIMS,'as_of':AS_OF,'text_locator_note':'Card prose is synthesis: owner section plus independent review pointer; exact numerical claims have direct field/CSV record locators.'})
    out_csv('claim_pointers.csv',CLAIMS)
    verify_structure(result,program,context,strategy,evidence)
    index=[{k:v for k,v in s.items() if k!='data'} for _,s in sorted(SOURCE.items())]
    out_json('source_manifest.json',{'schema':1,'as_of':AS_OF,'pins':PINS,'sources':index,'source_policy':'git show exactSHA:path only; no fetch, no moving ref, no whole-worktree copy; no historical rawhash repaired'})
    out_csv('source_index.csv',index)
    # Immutable source files and generated outputs are covered, manifest excludes itself.
    OUT['build.py']=Path(__file__).read_bytes();OUT['card_specs.json']=(HERE/'card_specs.json').read_bytes()
    manifest={'schema':1,'as_of':AS_OF,'scope':P+'dashboard_handoff/','outputs':[{'path':p,'bytes':len(b),'sha256':digest(b)} for p,b in sorted(OUT.items())],
              'self_excluded':'output_manifest.json','reproduce':'python3 '+P+'dashboard_handoff/build.py --verify',
              'qualification':'Serialization integrity, not independent model or final strategy acceptance.'}
    out_json('output_manifest.json',manifest)
    if args.verify:
        mismatches=[p for p,b in OUT.items() if not (HERE/p).is_file() or (HERE/p).read_bytes()!=b]
        actual={str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        extras=actual-set(OUT)
        if mismatches or extras:raise SystemExit('FAIL mismatches='+repr(mismatches)+' extras='+repr(sorted(extras)))
        print('PASS: '+str(len(OUT))+' delivered files; '+str(len(index))+' exact source blobs; 10 cards; no source/model execution; output bytes unchanged.')
    else:
        for p,b in OUT.items():
            target=HERE/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
        print('BUILT '+str(len(OUT))+' files from '+str(len(index))+' exact source blobs; write scope '+str(HERE))

if __name__=='__main__':main()
