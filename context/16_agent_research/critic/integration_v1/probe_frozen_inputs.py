#!/usr/bin/env python3
"""Independent first pass over phase2 frozen references; no peer code execution."""
import argparse
import csv
import datetime as dt
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import subprocess

BASE=Path(__file__).resolve().parent
CONTRACT_HASH='1ac53dc652120d8561415056afd0b7013f8fad4d20341b3b76cbd33502b6ab57'
CONTRACT_GIT_SHA='22cbc003ace80ca6ca6637b50f6faa11eb5586e1'

def write_json(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def table(data):return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
def write_csv(path,rows):
    with path.open('w',newline='')as f:
        writer=csv.DictWriter(f,list(rows[0]));writer.writeheader();writer.writerows(rows)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--peer-root',type=Path);args=parser.parse_args()
    for name in ['contract.json','input_manifest.json']:
        dest=BASE/('frozen_'+name)
        if not dest.exists():
            if args.peer_root is None:raise SystemExit('First capture requires --peer-root; later replays use frozen local metadata')
            dest.write_bytes((args.peer_root/name).read_bytes())
    contract_bytes=(BASE/'frozen_contract.json').read_bytes();assert hashlib.sha256(contract_bytes).hexdigest()==CONTRACT_HASH
    for name in ['contract.json','input_manifest.json']:
        published=subprocess.check_output(['git','show',CONTRACT_GIT_SHA+':context/16_agent_research/hypotheses/experiment_v1/'+name])
        assert (BASE/('frozen_'+name)).read_bytes()==published,name
    contract=json.loads(contract_bytes);manifest=json.loads((BASE/'frozen_input_manifest.json').read_text())
    refs={};receipts=[]
    for entry in manifest['inputs']:
        data=subprocess.check_output(['git','show',entry['source_git_sha']+':'+entry['source_path']])
        assert hashlib.sha256(data).hexdigest()==entry['sha256'],entry['input_id']
        path=BASE/'raw/frozen-001'/entry['stored_path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        refs[entry['input_id']]=data
        receipts.append(dict(input_id=entry['input_id'],input_git_sha=entry['source_git_sha'],input_repo_path=entry['source_path'],local_path=path.relative_to(BASE).as_posix(),sha256=entry['sha256'],bytes=len(data)))
    board=table(refs['core:azimuth_flight_instances.csv']);zones=table(refs['core:airport_timezone_join.csv'])
    selected=[r for r in board if {r['origin_name_raw'],r['destination_name_raw']}=={'Киров','Минеральные Воды'}]
    output=[];anchors=[]
    for row in selected:
        dep=dt.datetime.fromisoformat(row['departure_planned_local']);arr=dt.datetime.fromisoformat(row['arrival_planned_local'])
        output.append(dict(flight=row['flight_number_normalized'],origin=row['origin_name_raw'],destination=row['destination_name_raw'],departure_published=dep.isoformat(),arrival_published=arr.isoformat(),local_date_difference=(arr.date()-dep.date()).days,source_dataset=row['source_dataset_id'],source_row=row['source_row'],value_status='DERIVED',source_observation_kind=row['observation_kind'],date_derivation=row['year_status'],clock_basis=row['time_basis'],nonstop=row['nonstop_status'],december_rule_status='UNKNOWN_NOT_ESTABLISHED_BY_NOVEMBER_BOARD',performance_status='NOT_ACCEPTED'))
        if row['origin_name_raw']=='Киров':
            for nights in [7,10,14]:
                anchors.append(dict(source_flight=row['flight_number_normalized'],source_departure=dep.isoformat(),source_arrival=arr.isoformat(),nights=nights,departure_day_plus_N=(dep.date()+dt.timedelta(days=nights)).isoformat(),arrival_day_plus_N=(arr.date()+dt.timedelta(days=nights)).isoformat(),difference_days=(arr.date()-dep.date()).days,booked_checkin_date='UNKNOWN',booked_checkout_date='UNKNOWN',value_status='SCENARIO',interpretation='Calendar sensitivity of two assumed anchors; neither is an observed hotel reservation or December product'))
    write_csv(BASE/'reference_board_instances.csv',output);write_csv(BASE/'hotel_anchor_checks.csv',anchors)
    grid=[];scenarios=contract['frozen_scenarios'];nominal=scenarios['nominal_seats']
    for fare in scenarios['symmetric_oneway_net_fares_rub']:
        for variable in scenarios['per_journey_variable_expense_rub']:
            margin=Fraction(fare-variable)
            for gap in scenarios['residual_funding_gap_rub']:
                ratio=Fraction(gap,1)/(2*margin) if margin>0 else None
                q=max(0,-(-ratio.numerator//ratio.denominator)) if ratio is not None else (0 if gap<=0 else None)
                grid.append(dict(fare_per_oneway_journey_rub=fare,variable_per_journey_rub=variable,constant_residual_gap_per_period_rub=gap,margin_per_oneway_rub=int(margin),required_sales_each_direction=q,period_contribution_at_q_rub=2*q*int(margin)-gap if q is not None else None,period_contribution_at_q_minus1_rub=2*(q-1)*int(margin)-gap if q else None,single_product_nominal_bound=q<=nominal if q is not None else False,joint_local_transfer_capacity='NOT_EVALUATED_BY_SINGLE_PRODUCT_ORACLE',value_status='SCENARIO'))
    write_csv(BASE/'threshold_oracle.csv',grid)
    assert all(r['period_contribution_at_q_rub']>=0 and (r['required_sales_each_direction']==0 or r['period_contribution_at_q_minus1_rub']<0)for r in grid)
    scope=dict(created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),own_phase1_reference='69cdc8b520789020e4ea6a46f3ad14e7ea5f4f2e',contract_git_sha=CONTRACT_GIT_SHA,contract_sha256=CONTRACT_HASH,input_set_id=manifest['input_set_id'],peer_input_refs=manifest['refs'],inputs=receipts,train='NO_MODEL_FIT',holdout='NO_TARGET_LABELS; NO_PREDICTIVE_ACCURACY_OR_EDGE_ACCEPTED',new_external_inputs='Require new reference snapshot, never silent overwrite')
    write_json(BASE/'reference_scope.json',scope)
    summary=dict(generated_at_utc=scope['created_at_utc'],frozen_inputs_hash_pass=len(receipts),calendar_board_rows=len(board),C14_selected_rows=len(selected),december_C14_service_admission='UNKNOWN_NOVEMBER_BOARD_NOT_DECEMBER_SCHEDULE',C14_overnight_anchor_rows=len(anchors),timezone_scope=[{k:r[k]for k in ['airport_id','iata_code','iana_timezone','timezone_validation_status']}for r in zones if r['iata_code']in {'KVX','MRV'}],clock_basis='SOURCE_UNKNOWN; NO_UTC_OR_FLIGHT_DURATION_ACCEPTED',threshold_rows=len(grid),largest_single_product_q=max(r['required_sales_each_direction']for r in grid),scope='Exact conditional arithmetic only. No demand, realised yield, free aircraft or launch acceptance. Gap includes all candidate/baseline components only as a declared constant stress, not an estimated budget.')
    write_json(BASE/'first_pass.json',summary);print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
