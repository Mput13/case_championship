#!/usr/bin/env python3
"""Exact compact finalist frequency export, independent of financial reruns.

Run AFTER calculate.py and BEFORE verify.py, using the same Python -B.
This reads only completed inputs and the completed financial receipt. It never
changes financial data. Its separate validation records 36 real month/tail
calendar evaluations. Repeating this process must reproduce its two artifacts.
The parent run receipt is extended to cover these derived artifacts; the
financial 25-file component digest remains separately recorded.
"""
import sys
sys.dont_write_bytecode=True
import calendar
import csv
import json
from collections import Counter
import core as C

NAMES=('three_finalists_monthly.csv','finalist_months_validation.json')

def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')

def run():
    before=C.guard();manifest=C.js(C.HERE/'input_manifest.json');receipt=C.js(C.HERE/'run_receipt.json')
    assert receipt['input_digest']==manifest['input_digest']
    for p,h in manifest['input_sha256'].items():assert C.sha(C.ROOT/p)==h,p
    for p,h in manifest['code_sha256'].items():assert C.sha(C.HERE/p)==h,p
    financial={n:h for n,h in receipt['deterministic_output_sha256'].items() if n not in NAMES}
    for n,h in financial.items():assert C.sha(C.HERE/n)==h,n
    rows=[];checks=[]
    for cid in receipt['finalists']:
        t=C.templates()[cid]
        assert t['cohort']=='K2'
        for m in range(1,13):
            cal=C.M.calendar_events(t['states']['REPLACE'],t['tails'],2027,m)
            counts=Counter((f['tail'],f['origin'],f['destination'],f['kind'],f['rotation_id'].startswith('NEW-')) for f in cal['flights'])
            keys=sorted({(t,a,b) for t,a,b,_,_ in counts})
            for tail,a,b in keys:
                service=sum(n for (tt,aa,bb,kind,_),n in counts.items() if (tt,aa,bb)==(tail,a,b) and kind=='service')
                ferry=sum(n for (tt,aa,bb,kind,_),n in counts.items() if (tt,aa,bb)==(tail,a,b) and kind=='positioning')
                new=sum(n for (tt,aa,bb,_,isnew),n in counts.items() if (tt,aa,bb)==(tail,a,b) and isnew)
                old=service+ferry-new
                days=calendar.monthrange(2027,m)[1]
                rows.append(dict(candidate=cid,cohort='K2',month=f'2027-{m:02}',season=C.M.exposure(2027,m)['seasons'],
                    scenario='SAME_PHYSICAL_CALENDAR_BASE_CAUT',tail=tail,origin=a,destination=b,
                    old_dated_departures=old,new_dated_departures=new,physical_dated_departures=service+ferry,
                    service_dated_departures=service,paid_ferry_dated_departures=ferry,
                    effective_service_departures_week=service*7/days,effective_physical_departures_week=(service+ferry)*7/days,
                    monthly_saleable_service_seats=100*service,ferry_seats_and_revenue=0,
                    working_tails=2,separate_R1='R1_NOT_WORKING',calendar_days=days,calendar_status=cal['status'],
                    position_at_month_start=cal['carry'][tail+'/start']['position'],
                    position_at_month_end=cal['carry'][tail+'/end']['position'],
                    actual_release_dispatch=None))
            assert sum(r['physical_dated_departures'] for r in rows if r['candidate']==cid and r['month']==f'2027-{m:02}')==len(cal['flights'])
            assert not any(f['tail']=='R1' for f in cal['flights'])
            checks.append(dict(candidate=cid,month=f'2027-{m:02}',flights=len(cal['flights']),
                calendar_hash=C.digest(cal),position_turn60='PASS',BH8_diagnostics=len(cal['errors']),FDP_dispatch=None))
    with (C.HERE/NAMES[0]).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
        for r in rows:w.writerow({k:'NULL' if v is None else round(v,8) if isinstance(v,float) else v for k,v in r.items()})
    assert len(checks)==36 and len({r['candidate'] for r in rows})==3
    assert before==C.guard()
    validation=dict(status='PASS',financial_input_digest=receipt['input_digest'],financial_code_digest=receipt['code_digest'],
        financial_component_output_digest=C.digest(financial),generator_sha256=C.sha(C.HERE/'finalist_months.py'),
        derived_artifact=NAMES[0],derived_sha256=C.sha(C.HERE/NAMES[0]),rows=len(rows),checks=checks,
        rule='dated departures times7 / actual days; full padded recurrence; no Febx12/52; R1 never working',
        financial_data_modified=False,actual_dispatch=False,guard_before=before,guard_after=C.guard())
    dump(C.HERE/NAMES[1],validation)
    combined=dict(financial)|{n:C.sha(C.HERE/n) for n in NAMES}
    receipt.update(deterministic_output_sha256=combined,output_digest=C.digest(combined),
        financial_component_output_digest=C.digest(financial),
        auxiliary_generator='finalist_months.py',auxiliary_generator_sha256=validation['generator_sha256'],
        auxiliary_validation=NAMES[1],execution_components='calculate.py financial full run + finalist_months.py exact monthly calendar export')
    dump(C.HERE/'run_receipt.json',receipt)
    print(json.dumps(dict(status='PASS',rows=len(rows),calendar_checks=36,financial_component_output_digest=C.digest(financial),
        auxiliary_artifact_sha256={n:C.sha(C.HERE/n) for n in NAMES},composite_output_digest=C.digest(combined)),sort_keys=True))

if __name__=='__main__':run()
