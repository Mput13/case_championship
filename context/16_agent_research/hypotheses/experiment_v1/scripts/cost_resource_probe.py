#!/usr/bin/env python3
"""Reconcile matched-flight resource deltas and published tariff coefficients."""
from pathlib import Path
from datetime import datetime
from collections import Counter
from decimal import Decimal
import csv,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
RUN='c26661067277af20'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return list(csv.DictReader(p.open()))
def write(p,data):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
def minutes(a,b):return int((datetime.fromisoformat(a)-datetime.fromisoformat(b)).total_seconds()/60)
def main():
    base=ROOT/'runs'/RUN;manifest=json.loads((base/'output_manifest.json').read_text())
    for r in manifest['files']:assert sha(base/r['path'])==r['sha256']
    legs=rows(base/'physical_legs.csv');tariff_path=ROOT/'inputs/core/airport_cost_selected_verified.csv';tariffs=rows(tariff_path)
    source_manifest=json.loads((ROOT/'input_manifest.json').read_text())
    assert sha(tariff_path)==next(r['sha256'] for r in source_manifest['inputs'] if r['input_id']=='core:airport_cost_selected_verified.csv')
    inputs={'output_manifest_sha256':sha(base/'output_manifest.json'),'tariff_sha256':sha(tariff_path),'script_sha256':sha(Path(__file__)),'frozen_contract_sha256':sha(ROOT/'contract.json')}
    ident=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()[:16];out=ROOT/'cost_resource'/ident
    if out.exists():
        stored=json.loads((out/'manifest.json').read_text())
        for r in stored['outputs']:assert sha(out/r['path'])==r['sha256']
        print(json.dumps({'module_run':ident,'status':'REPLAY_HASH_MATCH'}));return
    out.mkdir(parents=True)
    deltas=[];counts=[]
    for tail in ['NORTH','SOUTH']:
        a=sorted([r for r in legs if r['variant']=='C01_unsync' and r['tail']==tail and r['leg_id'].rsplit('_',2)[1]=='2026-12-07'],key=lambda x:x['departure_utc'])
        b=sorted([r for r in legs if r['variant']=='C01_sync' and r['tail']==tail and r['leg_id'].rsplit('_',2)[1]=='2026-12-07'],key=lambda x:x['departure_utc'])
        deltas.append(dict(candidate='C01',unit='one operating date; 2026-12-07',resource=tail,baseline='unsync',candidate_program='sync',
            delta_block_minutes=sum(int(r['block_minutes']) for r in b)-sum(int(r['block_minutes']) for r in a),
            delta_elapsed_minutes=minutes(b[-1]['arrival_utc'],b[0]['departure_utc'])-minutes(a[-1]['arrival_utc'],a[0]['departure_utc']),
            first_departure_shift_minutes=minutes(b[0]['departure_utc'],a[0]['departure_utc']),return_shift_minutes=minutes(b[-1]['arrival_utc'],a[-1]['arrival_utc']),
            physical_flight_count_delta=len(b)-len(a),money_effect_rub='',money_status='UNKNOWN',value_type='DERIVED_FROM_SCENARIO',caveat='15 extra occupied minutes may move final return by135 minutes; equal totals do not prove a compatible next assignment'))
    for row in rows(base/'c07_comparison.csv'):
        deltas.append(dict(candidate='C07',unit='one four-leg rotation vs two-leg reference',resource='CHAIN',baseline=row['baseline'],candidate_program=row['variant'],
            delta_block_minutes=int(row['block_candidate_minutes'])-int(row['block_baseline_minutes']),delta_elapsed_minutes=int(row['elapsed_candidate_minutes'])-int(row['elapsed_baseline_minutes']),
            first_departure_shift_minutes=0,return_shift_minutes=int(row['return_delay_vs_reference_minutes']),physical_flight_count_delta=2,money_effect_rub='',money_status='UNKNOWN',value_type='DERIVED_FROM_SCENARIO_WITH_SOURCE_CLOCKS',caveat='Return displacement and alternative use of the aircraft window must be priced; no real donor selected'))
    for candidate,baseline,proposed in [('C01','C01_unsync','C01_sync'),('C07','C07_reference','C07_chain_turn45')]:
        selected={name:[r for r in legs if r['variant']==name and (candidate!='C01' or r['leg_id'].rsplit('_',2)[1]=='2026-12-07')] for name in [baseline,proposed]}
        airports=sorted({r[k] for v in selected.values() for r in v for k in ['origin','destination']})
        for airport in airports:
            for activity,col in [('departure','origin'),('arrival','destination')]:
                a=sum(r[col]==airport for r in selected[baseline]);b=sum(r[col]==airport for r in selected[proposed])
                counts.append(dict(candidate=candidate,airport=airport,activity=activity,baseline_count=a,proposed_count=b,delta_count=b-a,unit='physical events per compared rotation/date',billing_events='UNKNOWN_NOT_EQUAL_TO_MOVEMENTS_AUTOMATICALLY',value_type='DERIVED_FROM_SCENARIO'))
    write(out/'matched_resource_deltas.csv',deltas);write(out/'movement_count_deltas.csv',counts)
    selected=[]
    for r in tariffs:
        if r['airport_iata'] in ['UFA','OMS'] and r['item'] in ['takeoff_landing','transport_security','terminal_domestic','passenger_service_domestic','terminal_domestic_adult','passenger_service_domestic_adult','temporary_parking_SSJ']:
            selected.append({k:r[k] for k in ['source_dataset_id','airport_iata','effective_from','known_on','item','value','unit','VAT_basis','scope','value_status','validation_scope']})
    write(out/'published_tariff_references.csv',selected)
    coefficients=[]
    for airport in ['OMS','UFA']:
        rates=[r for r in tariffs if r['airport_iata']==airport and r['item'] in ['takeoff_landing','transport_security']]
        assert len(rates)==2 and all(r['unit']=='RUB/t MTOW' for r in rates)
        coefficients.append(dict(airport=airport,reference_coefficient=sum(Decimal(r['value']) for r in rates),unit='RUB/t MTOW if each named published charge billed once',components='takeoff_landing + transport_security',value_type='DERIVED_PUBLISHED_RATE_SUM',paid_budget_rub='',budget_status='UNKNOWN',billing_multiplicity='UNKNOWN',discount_contract='UNKNOWN',MTOW_variant='UNKNOWN',VAT_treatment='UNKNOWN',use='Coefficient only, not cost floor or RW invoice. UFA same movements does not make base/parking/connection costs zero.'))
    write(out/'conditional_tariff_coefficients.csv',coefficients)
    gap=[
        dict(candidate='C01',baseline='same four hypothetical legs unsync',residual_gap='(flight_cost_sync-flight_cost_unsync) + delta_ground/base/overnight/reserve/switching + (local_revenue_minus_paxcost_unsync-local_revenue_minus_paxcost_sync) + lost_contribution_of_other_retained_RW',common_leg_cost_rule='Cancel identical costs once if input/resource/contract equal; do not charge four whole flights again for synchronization',unknowns='all incremental prices, current baseline feasibility, protected transfer sale and local sales loss',status='UNKNOWN'),
        dict(candidate='C07',baseline='same SVX-OMS-SVX reference',residual_gap='(full_chain_flight_cost-reference_flight_cost) + delta_ground/fixed/switching/opportunity + (reference_local_revenue_minus_paxcost-chain_local_revenue_minus_paxcost) + other_retained_network_loss',common_leg_cost_rule='Every new OMS-KJA leg and extra ground event included; unchanged reference legs cancel only if their costs really unchanged',unknowns='RW engineering block, fuel, crew, next assignment, changed return local sales, actual donor',status='UNKNOWN'),
        dict(candidate='C14',baseline='preserve actual network; add proposed four-leg chain',residual_gap='full_SVX_KVX_MRV_KVX_SVX_cost + incremental_fixed/positioning/opportunity - contribution_of_other_new_products_before_flight_cost + retained_network_loss',common_leg_cost_rule='SVX-KVX base legs have costs and unknown other-product contribution; no free positioning. A real replacement requires a different observed donor baseline.',unknowns='both directional winter products, full chain cost, free resource, other-product sales, net fare, obligations',status='UNKNOWN')]
    write(out/'residual_gap_accounting.csv',gap)
    product_definitions=[
        dict(candidate='C01',itinerary_template_id='C01_NJC_MRV_VIA_UFA_RETURN',target_origin='NJC',target_destination='MRV',outward_leg_sequence='NJC>UFA;UFA>MRV',return_leg_sequence='MRV>UFA;UFA>NJC',legs_per_oneway_journey=2,excluded_revenue='Local one-leg sales belong to baseline/lost contribution; not included in target q'),
        dict(candidate='C07',itinerary_template_id='C07_LOCAL_OMS_KJA_RETURN',target_origin='OMS',target_destination='KJA',outward_leg_sequence='OMS>KJA',return_leg_sequence='KJA>OMS',legs_per_oneway_journey=1,excluded_revenue='SVX-OMS locals and SVX-KJA through sales excluded from target q; through product would consume two legs per direction'),
        dict(candidate='C14',itinerary_template_id='C14_LOCAL_KVX_MRV_RETURN',target_origin='KVX',target_destination='MRV',outward_leg_sequence='KVX>MRV',return_leg_sequence='MRV>KVX',legs_per_oneway_journey=1,excluded_revenue='SVX-KVX base-leg and through sales are separate unknown contributions; all four flight costs remain in gap')]
    write(out/'money_product_definitions.csv',product_definitions)
    lookup={r['candidate']:r for r in product_definitions};explicit=[]
    for r in rows(base/'conditional_thresholds.csv'):
        d=lookup[r['candidate']]
        assert int(r['physical_boardings'])==int(r['total_oneway_journeys'])*d['legs_per_oneway_journey']
        explicit.append({**r,**{k:v for k,v in d.items() if k!='candidate'},'dated_cohort_scope':'TEMPLATE_INVERSION_ONLY; allocate actual costs across a named departure/return cohort before use'})
    write(out/'conditional_thresholds_with_product_keys.csv',explicit)
    checks={'block_delta_C01_zero':all(r['delta_block_minutes']==0 for r in deltas if r['candidate']=='C01'),'C07_extra_block270':all(r['delta_block_minutes']==270 for r in deltas if r['candidate']=='C07'),'C07_OMS_extra_arrival_and_departure':all(r['delta_count']==1 for r in counts if r['candidate']=='C07' and r['airport']=='OMS'),'OMS_reference1858':str(coefficients[0]['reference_coefficient'])=='1858','no_invoice_or_gap_imputed':all(not r['paid_budget_rub'] for r in coefficients) and all(r['status']=='UNKNOWN' for r in gap)}
    assert all(checks.values());(out/'checks.json').write_text(json.dumps({'status':'PASS','checks':checks,'scope':'arithmetic/accounting structure only'},indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({'module_run':ident,'inputs':inputs,'outputs':[{'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()]},indent=2)+'\n')
    print(json.dumps({'module_run':ident,'status':'PASS','resource_rows':len(deltas),'movement_delta_rows':len(counts),'tariff_reference_rows':len(selected)}))
if __name__=='__main__':main()
