#!/usr/bin/env python3
"""Independent units/provenance check of stage19; no author code execution."""
import csv
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess

BASE=Path(__file__).resolve().parents[1]
SHA='0a16cbcd12535c759a7dc2b127f60c32aae057e6'
PREFIX='context/19_demand_mechanisms/'
CAPTURE=[]

def blob(path):
    data=subprocess.check_output(['git','show',SHA+':'+path])
    dest=BASE/'raw/stage19'/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    CAPTURE.append(dict(input_sha=SHA,repo_path=path,local_path=dest.relative_to(BASE).as_posix(),
                        sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
    return data

def read(name):return json.loads(blob(PREFIX+name))
def table(name):return list(csv.DictReader(io.StringIO(blob(PREFIX+name).decode('utf-8-sig'))))

def main():
    assumptions=read('assumptions.json');cases=read('findings.json');sources=read('evidence/sources.json')
    inventory=table('case_inventory.csv');proposals=table('model_change_proposals.csv');quantities=table('quantity_scenarios.csv');current=table('current_model_inputs.csv')
    declared=read('input_manifest.json')['sha256'];hash_checks=[]
    for path,expected in declared.items():
        data=subprocess.check_output(['git','show',SHA+':'+path])
        hash_checks.append(dict(repo_path=path,expected_sha256=expected,actual_sha256=hashlib.sha256(data).hexdigest()))
    breakeven=list(csv.DictReader(io.StringIO(blob('context/18_unit_economics_audit/breakeven.csv').decode())))
    gate=next(r for r in breakeven if r['route']=='SVX-MRV' and r['scenario']=='base' and r['weekly_extra_burden']=='0')
    extra=math.ceil(float(gate['required_paid_ceil_if_feasible'])-float(gate['paid_now_per_departure']))
    ids={s['id'] for s in sources};errors=[];expected=[]
    for case in cases[:2]:
        row=next(r for r in quantities if r['case']==case['id'])
        value=case['people_count']*2*assumptions['cohort_round_trips_scenario_per_person']
        expected.append(dict(case=case['id'],expected_person_movements=value,exported=float(row['output'])))
        if float(row['output'])!=value:errors.append(case['id']+'_cohort_units')
    hotel=[]
    for row in [r for r in quantities if r['case']=='C03']:
        turnover=112*assumptions['hotel_room_guests_scenario']*float(row['occupancy_scenario'])*7/assumptions['hotel_mean_stay_days_scenario']
        fraction=extra/turnover
        hotel.append(dict(occupancy_scenario=float(row['occupancy_scenario']),arrivals_all_modes_all_origins=turnover,
                          extra_paid_per_departure_to_existing_variable_gate=extra,combined_fraction_scenario=fraction))
        if not math.isclose(float(row['output']),turnover) or not math.isclose(float(row['required_combined_origin_air_RW_net_new_date_fit_fraction']),fraction):errors.append('hotel_units')
    shift=assumptions['shift_example_unique_people']*7/(assumptions['shift_example_on_days']+assumptions['shift_example_off_days'])
    if float(next(r for r in quantities if r['case']=='C07_FORMULA_ONLY')['output'])!=shift:errors.append('shift_units')
    changed=subprocess.check_output(['git','diff','--name-only','359ad3cfb4fdcc74e14c802fc6256e65c1106dbb',SHA],text=True).splitlines()
    previous_numeric_changed=[p for p in changed if p.startswith(('context/12_','context/15_','context/16_','context/17_','context/18_'))]
    out=dict(generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),input_sha=SHA,author='mput',
        policy='Read pinned exports and independent formulas; no author code executed',
        cases=len(cases),shortlisted=sum(bool(c['shortlist']) for c in cases),sources=len(sources),
        source_ids_resolve=all(s in ids for c in cases for s in c['sources']),
        inventory_paid_OD_unknown=all(r['new_paid_OD_target_week']=='' and r['OD_status']=='UNKNOWN_NOT_ZERO' for r in inventory),
        proposals_numeric_OD_yield_unknown=all(r['new_paid_OD_value']==r['new_net_yield_value']=='' for r in proposals),
        automatic_OD_updates=any(r['automatic_OD_or_city_rank_boost']=='True' for r in proposals),
        cohort_units=expected,hotel_units=hotel,shift_example_arrivals_per_direction=shift,arithmetic_errors=errors,
        current_model_rows=len(current),previous_numeric_files_changed=previous_numeric_changed,
        declared_input_hashes_checked=len(hash_checks),input_hash_mismatches=[r for r in hash_checks if r['expected_sha256']!=r['actual_sha256']],
        primary_scope='Direct source checks recorded separately in evidence/stage19_primary_checks.json; indexed-body availability is not raw acquisition',
        limits='No paid air OD, city origin split, winter cohort, contract net yield, free aircraft, forecast or new strategy accepted')
    (BASE/'evidence/stage19_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    (BASE/'evidence/stage19_input_manifest.json').write_text(json.dumps(dict(input_sha=SHA,files=CAPTURE,declared_hash_checks=hash_checks),indent=2)+'\n')
    assert not errors and not out['input_hash_mismatches'] and not previous_numeric_changed
    assert out['inventory_paid_OD_unknown'] and out['proposals_numeric_OD_yield_unknown'] and not out['automatic_OD_updates']
    print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__':main()
