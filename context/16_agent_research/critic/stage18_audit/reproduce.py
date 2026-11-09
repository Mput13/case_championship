#!/usr/bin/env python3
"""Independent export arithmetic and residual-seat LP review. No foreign imports."""
import collections
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import platform
import scipy
from scipy.optimize import linprog

BASE=Path(__file__).resolve().parent
MODEL=BASE/'raw/context/18_unit_economics_audit'
PREV=BASE/'raw/context/17_aircraft_route_review'
def read(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def n(r,k):
    assert r[k] not in ('',None), (k,r)
    x=float(r[k]);assert math.isfinite(x)
    return x
def close(a,b):return math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=1e-4)

def main():
    manifest=json.loads((BASE/'input_manifest.json').read_text())
    assert all(hashlib.sha256((BASE/e['local_path']).read_bytes()).hexdigest()==e['sha256'] for e in manifest['files'])
    errors=[];counts=collections.Counter()
    def check(cat,loc,field,a,b):
        counts[cat]+=1
        if not close(a,b):errors.append(dict(category=cat,locator=loc,field=field,exported=a,recomputed=b))
    registry=read(MODEL/'input_registry.csv');params={s:{r['parameter']:float(r[s]) for r in registry if r['parameter'] in ['fuel_t_per_hour','fuel_t_per_cycle','fuel_rub_per_t','fuel_uplift_rub_per_t','mro_rub_per_hour','crew_rub_per_hour','navigation_rub_per_hour','pax_cost','airport_factor','deicing_probability','deicing_operation_rub','capture_uncertain','frequency_scale','old_RW_fare_ratio']} for s in ['base','cautious']}
    ledgers=read(MODEL/'route_ledger.csv');costs=read(MODEL/'flight_cost_components.csv');by={(r['route'],r['scenario']):r for r in ledgers};parts=['fuel_product','fuel_uplift','mro','crew','navigation','airport_turn','deicing']
    def flight(minutes,p):
        h=minutes/60;tons=h*p['fuel_t_per_hour']+p['fuel_t_per_cycle']
        return dict(block_hours=h,fuel_t=tons,fuel_product=tons*p['fuel_rub_per_t'],fuel_uplift=tons*p['fuel_uplift_rub_per_t'],mro=h*p['mro_rub_per_hour'],crew=h*p['crew_rub_per_hour'],navigation=h*p['navigation_rub_per_hour'],airport_turn=(49.45*(553+499)+19300+8100+16668)*p['airport_factor'],deicing=p['deicing_probability']*p['deicing_operation_rub'])
    units={}
    for r in costs:
        loc='flight_cost_components.csv:'+r['route']+':'+r['scenario']+':'+r['origin'];f=flight(n(r,'block_minutes'),params[r['scenario']])
        for k,v in f.items():check('flight_costs',loc,k,n(r,k),v)
        check('flight_costs',loc,'flight_total',n(r,'flight_total'),sum(f[k] for k in parts))
    for r in ledgers:
        key=(r['route'],r['scenario']);p=params[r['scenario']];can=n(r,'migration_share');oldlegs=1 if r['route'] in ['SVX-REN','SVX-OMS'] else 2
        q=n(r,'paid_per_departure');fare=n(r,'assumed_fare');margin=fare*(1-can*p['old_RW_fare_ratio'])-p['pax_cost']*(1-oldlegs*can);units[key]=(margin,p['pax_cost']*(1-oldlegs*can))
        ff=[x for x in costs if (x['route'],x['scenario'])==key];loc='route_ledger.csv:'+':'.join(key)
        for k in parts+['fuel_t']:check('route_costs',loc,k,n(r,k),sum(n(x,k) for x in ff))
        F=sum(n(x,'flight_total') for x in ff)
        vals=dict(sold_journeys=2*q,gross_revenue=2*q*fare,foregone_RW_revenue=2*q*can*fare*p['old_RW_fare_ratio'],new_pax_variable=2*q*p['pax_cost'],saved_old_pax_variable=2*q*can*oldlegs*p['pax_cost'],flight_variable_cost=F,incremental_revenue=2*q*fare*(1-can*p['old_RW_fare_ratio']),contribution_before_base_fleet_opportunity=2*q*margin-F)
        for k,v in vals.items():check('route_money',loc,k,n(r,k),v)
        cap=p['capture_uncertain']*(1-math.exp(-1/p['frequency_scale']))
        check('capture',loc,'paid_per_departure',q,min(100,n(r,'assumed_weekly_OD_direction')*cap))
    be=read(MODEL/'breakeven.csv')
    for r in be:
        key=(r['route'],r['scenario']);src=by[key];p=params[r['scenario']];margin,netpax=units[key];f=n(r,'frequency_per_direction');F=n(src,'flight_variable_cost')+n(r,'weekly_extra_burden');q=n(src,'paid_per_departure');fare=n(src,'assumed_fare');can=n(src,'migration_share');raw=F/(2*f*margin);capture=p['capture_uncertain']*(1-math.exp(-f/p['frequency_scale']));loc='breakeven.csv:'+':'.join(key)+':'+r['weekly_extra_burden']
        vals=dict(unit_incremental_margin_current_yield=margin,linear_paid_threshold_NOT_capacity_forecast=raw,new_net_yield_needed_at_same_sales_old_RW_yield_fixed=F/(2*f*q)+netpax+can*fare*p['old_RW_fare_ratio'],common_new_and_old_net_yield_needed_at_same_sales=(F/(2*f*q)+netpax)/(1-can*p['old_RW_fare_ratio']),contribution_at100_and_current_fare=2*f*100*margin-F,net_fuel_benefit_needed_at_current_sales=max(0,(-n(src,'contribution_before_base_fleet_opportunity')+n(r,'weekly_extra_burden'))/n(src,'fuel_t')))
        for k,v in vals.items():check('breakeven',loc,k,n(r,k),v)
        if (r['within_nominal100']=='True') != (raw<=100):errors.append(dict(category='breakeven',locator=loc,error='capacity flag'))
        if raw<=100:
            check('breakeven',loc,'required_paid_ceil_if_feasible',n(r,'required_paid_ceil_if_feasible'),math.ceil(raw))
            check('breakeven',loc,'required_OD_week_direction_if_capture_unchanged',n(r,'required_OD_week_direction_if_capture_unchanged'),raw*f/capture)
        else:
            assert r['required_paid_per_departure_if100_feasible']==r['required_OD_week_direction_if_capture_unchanged']==''
        for d,col in [(r['route'].split('-')[0],'required_outbound'),(r['route'].split('-')[1],'required_inbound')]:
            direction=next(x for x in costs if(x['route'],x['scenario'],x['origin'])==(*key,d))
            check('breakeven',loc,col,n(r,col),(n(direction,'flight_total')+n(r,'weekly_extra_burden')/(2*f))/margin)
    credits=read(MODEL/'net_fuel_adjustments.csv')
    for r in credits:
        src=by[(r['route'],r['scenario'])];delta=n(r,'net_fuel_benefit_rub_per_t')*n(src,'fuel_t');loc='net_fuel_adjustments.csv:'+r['route']+':'+r['scenario']+':'+r['net_fuel_benefit_rub_per_t']
        check('net_fuel',loc,'delta',n(r,'extra_income_or_cost_reduction'),delta);check('net_fuel',loc,'contribution',n(r,'contribution'),n(src,'contribution_before_base_fleet_opportunity')+delta)
    freq=read(MODEL/'frequency_tests.csv')
    for r in freq:
        key=(r['route'],r['scenario']);src=by[key];p=params[r['scenario']];f=n(r,'frequency_per_direction');paid=min(100,n(src,'assumed_weekly_OD_direction')*p['capture_uncertain']*(1-math.exp(-f/p['frequency_scale']))/f);loc='frequency_tests.csv:'+':'.join(key)+':'+str(f)
        check('frequency',loc,'paid',n(r,'paid_per_departure'),paid);check('frequency',loc,'contribution',n(r,'contribution'),2*f*paid*units[key][0]-f*n(src,'flight_variable_cost'))
    anchors={r['route']:n(r,'value') for r in read(MODEL/'evidence/observed_pair_segments.csv') if r['period']=='2025'}
    scales=read(MODEL/'source_linked_scale_tests.csv')
    for r in scales:
        key=(r['route'],r['scenario']);src=by[key];p=params[r['scenario']];D=anchors[r['route']]/104*n(r,'endpoint_fraction')*n(r,'winter_to_annual_ratio');q=p['capture_uncertain']*(1-math.exp(-1/p['frequency_scale']));paid=min(100,D*q);loc='source_linked_scale_tests.csv:'+':'.join(key)+':'+r['endpoint_fraction']+':'+r['winter_to_annual_ratio']
        for k,v in dict(assumed_OD_week_direction=D,paid_per_departure=paid,contribution_before_extra_fixed=2*paid*units[key][0]-n(src,'flight_variable_cost')).items():check('source_linked',loc,k,n(r,k),v)
    for r in read(MODEL/'source_linked_scale_gates.csv'):
        reference=anchors[r['route']]/104;key=(r['route'],r['scenario']);threshold=next(v for v in be if(v['route'],v['scenario'],v['weekly_extra_burden'])==(*key,'0'));loc='source_linked_scale_gates.csv:'+':'.join(key)
        check('source_gate',loc,'historical_segment_reference',n(r,'historical_segment_reference_per_week_direction'),reference)
        if threshold['within_nominal100']=='True':check('source_gate',loc,'eta_times_season',n(r,'required_endpoint_fraction_times_winter_ratio'),n(threshold,'required_OD_week_direction_if_capture_unchanged')/reference)
        else:assert r['required_endpoint_fraction_times_winter_ratio']==''
    previous=read(MODEL/'previous_reconciliation.csv');stage17=read(PREV/'model/comparison.csv');orig={(r['profile'],r['network'],r['scenario']):r for r in stage17}
    for r in previous:
        loc='previous_reconciliation.csv:'+r['profile']+':'+r['network']+':'+r['scenario'];s=orig[(r['profile'],r['network'],r['scenario'])]
        if r['network']=='NO_LAUNCH':
            # Explicit structural baseline, not general missing-value imputation.
            for k in ['flight_cost','incremental_revenue','incremental_operating_cost','contribution']:check('no_launch_structural_baseline',loc,k,n(r,k),0)
            for k in ['gross_revenue','foregone_RW_revenue','sold_journeys','transfer_journeys','segment_pax']:check('no_launch_structural_baseline',loc,k,n(s,k),0)
            continue
        for dest,field in [('gross','gross_revenue'),('foregone','foregone_RW_revenue'),('journeys','sold_journeys'),('transfer','transfer_journeys'),('segment_pax','segment_pax'),('flight_cost','flight_variable_cost'),('contribution','contribution_before_base_fleet_opportunity')]:check('prior_export',loc,dest,n(r,dest),n(s,field))
        check('prior_export',loc,'cost_components',n(r,'flight_cost'),sum(n(r,k) for k in parts))
        check('prior_export',loc,'delta',n(r,'contribution'),n(r,'gross')-n(r,'foregone')-n(r,'flight_cost')-n(r,'pax_cost')+n(r,'saved_pax'))
    # Independent HiGHS LP versus the author's residual shortest-path algorithm.
    sales=read(PREV/'model/sales.csv');caps=read(PREV/'model/capacity.csv');bounds=[]
    for r in read(MODEL/'hub_transfer_optimistic_bound.csv'):
        key=('ROUTE_INPUTS_UPPER_100',r['network'],r['scenario']);ss=[x for x in sales if(x['profile'],x['network'],x['scenario'])==key];cc=[x for x in caps if(x['profile'],x['network'],x['scenario'])==key];used=collections.Counter();locals_q=0
        for s in ss:
            if s['transfer']=='False':
                locals_q+=n(s,'sold_journeys')
                for leg in s['flight_ids'].split(';'):used[leg]+=n(s,'sold_journeys')
        residual={x['flight_id']:n(x,'capacity_scenario')-used[x['flight_id']] for x in cc};edges={}
        for s in ss:
            if s['transfer']=='True':
                a,b=s['flight_ids'].split(';');edges[a,b]=n(s,'fare_once')-2*params[r['scenario']]['pax_cost']
        products=list(edges);flight_ids=list(residual);A=[[int(leg in e) for e in products] for leg in flight_ids];b=[residual[leg] for leg in flight_ids];c=[-edges[e] for e in products]
        result=linprog(c,A_ub=A,b_ub=b,bounds=(0,None),method='highs');assert result.success,result.message
        gain=-result.fun;loc='hub_transfer_optimistic_bound.csv:'+r['network']+':'+r['scenario'];check('hub_lp',loc,'fixed_locals',n(r,'fixed_local_journeys'),locals_q);check('hub_lp',loc,'transfer_margin',n(r,'optimistic_transfer_margin'),gain);check('hub_lp',loc,'total',n(r,'optimistic_total_contribution'),n(r,'local_only_contribution')+gain)
        dual=-sum(v*dual for v,dual in zip(b,result.ineqlin.marginals));check('hub_lp',loc,'primal_dual',gain,dual)
        bounds.append(dict(network=r['network'],scenario=r['scenario'],products=len(products),constraints=len(A),recomputed_margin=gain,exported_margin=n(r,'optimistic_transfer_margin'),dual_objective=dual,max_constraint_violation=max(0,max(-v for v in result.ineqlin.residual)),scope='Locals fixed, existing dated products, no transfer OD bound/migration; not whole-network bound'))
    examples=[{k:r[k] for k in ['route','scenario','paid_now_per_departure','linear_paid_threshold_NOT_capacity_forecast','common_new_and_old_net_yield_needed_at_same_sales','contribution_at100_and_current_fare']} for r in be if r['weekly_extra_burden']=='0' and r['scenario']=='base']
    out=dict(generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),input_sha=manifest['input_sha'],status='ARITHMETIC_PASS_SCOPED' if not errors else 'MISMATCH',execution_policy='No author code imported/executed. Stdlib re-derivation and independently implemented HiGHS linear programme.',environment=dict(python=platform.python_version(),scipy=scipy.__version__),checks=dict(counts),errors=errors,tables_checked=dict(route_ledgers=len(ledgers),flight_costs=len(costs),break_even=len(be),net_fuel_adjustments=len(credits),frequency_tests=len(freq),source_linked_scales=len(scales),prior_exports=len(previous)),hub_lp=bounds,examples=examples,limits=['No observed net realised yield, winter endpoint OD, payable tax benefit, actual mission fuel, free tail, fixed/opportunity budget or dispatch approval validated.','Primary public passenger figures corroborate reported historical route scale only.','Scenarios are not confidence limits; frozen locals residual LP is not a universal or global hub bound.'])
    (BASE/'reproduction.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:out[k] for k in ['status','checks','tables_checked','errors','hub_lp']},ensure_ascii=False))

if __name__=='__main__':main()
