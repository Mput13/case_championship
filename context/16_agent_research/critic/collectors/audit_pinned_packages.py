#!/usr/bin/env python3
"""Independent exported-ledger checks. Does not import or execute colleague code."""
import collections
import csv
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess

BASE=Path(__file__).resolve().parents[1]
PACKAGES={
 'stage15':('83c2698ebebc172fd8f1d0b8a82b8bd07f8da791','context/15_team_update/model',
            {'totals':'network_comparison.csv','sales':'itinerary_sales.csv','capacity':'flight_capacity.csv','flights':'project_flights.csv'}),
 'stage16':('bf564c7b66a2559c21e9f519ae5a3f28a489378f','context/16_conditional_decision/model',
            {'totals':'comparison.csv','sales':'sales.csv','capacity':'capacity.csv','flights':'flights.csv'})}

def blob(sha,path):
    data=subprocess.check_output(['git','show',f'{sha}:{path}'])
    dest=BASE/'raw'/'pinned_ledgers'/sha/path
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    return data

def rows(sha,path):return list(csv.DictReader(io.StringIO(blob(sha,path).decode('utf-8-sig'))))
def close(a,b):return math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=1e-4)
def key(r):return tuple(r.get(x,'local_first') for x in ['network','scenario','priority'])
def number(r,k):return float(r.get(k) or 0)

def audit(label,sha,root,names):
    tables={k:rows(sha,root+'/'+p) for k,p in names.items()}
    reports=[];errors=[];totals=tables['totals'];sales=tables['sales'];caps=tables['capacity'];flights=tables['flights']
    byid={r['id']:r for r in flights};assert len(byid)==len(flights)
    for t in totals:
        kk=key(t);ss=[r for r in sales if key(r)==kk];cc=[r for r in caps if key(r)==kk]
        checks={}
        for field in ['sold_journeys','transfer_journeys','segment_pax','gross_revenue','foregone_RW_revenue','incremental_revenue','new_pax_variable','saved_old_pax_variable','migrated_RW_total']:
            checks['sum_'+field]=close(number(t,field),sum(number(s,field) for s in ss))
        checks['revenue_delta']=close(number(t,'gross_revenue')-number(t,'foregone_RW_revenue'),number(t,'incremental_revenue'))
        checks['cost_delta']=close(number(t,'flight_variable_cost')+number(t,'new_pax_variable')-number(t,'saved_old_pax_variable'),number(t,'incremental_operating_cost'))
        checks['contribution']=close(number(t,'incremental_revenue')-number(t,'incremental_operating_cost'),number(t,'contribution_before_base_fleet_opportunity'))
        checks['journey_segment_identity']=close(number(t,'sold_journeys')+number(t,'transfer_journeys'),number(t,'segment_pax'))
        used=collections.Counter();od=collections.Counter();demand={}
        for s in ss:
            ids=s['flight_ids'].split(';');pax=number(s,'sold_journeys');tr=s['transfer']=='True'
            assert len(ids)==(2 if tr else 1)
            assert close(pax*number(s,'effective_fare'),number(s,'gross_revenue'))
            assert byid[ids[0]]['origin']==s['origin'] and byid[ids[-1]]['destination']==s['destination']
            if tr:
                a,b=[byid[i] for i in ids]
                assert a['destination']==b['origin']
                assert close(number(b,'departure_utc_minute')-number(a,'arrival_utc_minute'),number(s,'wait_minutes'))
            for i in ids:used[i]+=pax
            od[(s['origin'],s['destination'])]+=pax;demand[(s['origin'],s['destination'])]=number(s,'D_OD_week_direction')
        checks['dated_seats_and_od']=all(close(used[c['id']],number(c,'sold_segment_pax')) and used[c['id']]<=number(c,'capacity')+1e-6 for c in cc) and all(q<=demand[k]+1e-6 for k,q in od.items())
        checks['one_itinerary_fare']=True
        if not all(checks.values()):errors.append({'key':kk,'failed':[k for k,v in checks.items() if not v]})
        reports.append({'network':kk[0],'scenario':kk[1],'priority':kk[2],'all_arithmetic_checks_pass':all(checks.values()),'checks':checks,'contribution_before_base_fleet_opportunity':number(t,'contribution_before_base_fleet_opportunity')})
    return {'package':label,'sha':sha,'status':'ARITHMETIC_PASS' if not errors else 'FAIL','results_checked':len(totals),'sales_rows':len(sales),'flight_rows':len(flights),'errors':errors,'results':reports,'limits':'Exported ledgers reconciled independently. No source authenticity, realised OD/fare, future demand, contract or launch validation.'}

def main():
    outputs=[audit(label,*p) for label,p in PACKAGES.items()]
    stage16=PACKAGES['stage16'];sha,root,_=stage16
    routes=rows(sha,root+'/routes.csv');d=[r for r in routes if r['network']=='D_case8']
    direct_scope={'network':'D_case8','all_physical_pairs':len(d),'moscow_support_pairs':[r['pair'] for r in d if 'ZIA' in r['pair'].split('-')],
        'non_moscow_pairs':[r['pair'] for r in d if 'ZIA' not in r['pair'].split('-')],
        'interpretation':'Support flights are priced but should be distinguished from the interregional bypass-Moscow objective; route-count interpretation needs disclosure, not automatic rejection.'}
    gates=rows(sha,root+'/pilot_booking_gate.csv')
    gate_check=[]
    for r in gates:
        margin=number(r,'net_new_margin_per_booked');cost=number(r,'flight_cost');q=number(r,'required_paid_pax_before_fixed')
        assert close(q*margin,cost)
        gate_check.append({'origin':r['origin'],'destination':r['destination'],'scenario':r['scenario'],'required_before_fixed':q,
            'capacity':number(r,'capacity'),'required_ceiling':math.ceil(q),'paid_before_fixed_plus_10percent_variable_cost':math.ceil(1.1*q),
            'passes_capacity_before_fixed':q<=number(r,'capacity'),'note':'Arithmetic threshold only; payment/refund/time-to-departure/demand/migration assumptions unverified.'})
    result={'generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'execution_policy':'No colleague code executed; git-show blobs and independent stdlib calculations only',
            'packages':outputs,'direct_scope':direct_scope,'pilot_gate_reconciliation':gate_check}
    dest=BASE/'evidence'/'pinned_package_checks.json';dest.parent.mkdir(exist_ok=True);dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'packages':[{'package':o['package'],'status':o['status'],'results_checked':o['results_checked']}for o in outputs],'direct_scope':direct_scope,'pilot_gates':gate_check},ensure_ascii=False))

if __name__=='__main__':main()
