#!/usr/bin/env python3
"""A scoped counterexample: monetary threshold is not joint seat feasibility."""
import csv
import datetime as dt
import hashlib
import io
import json
import math
import subprocess
from fractions import Fraction
from pathlib import Path

BASE=Path(__file__).resolve().parent
SHA='eac4ed472c834c8520e94ebeff160211d1f675e2'
ROOT='context/16_agent_research/hypotheses/experiment_v1/'
MONEY=ROOT+'cost_resource/6cf441ef38e2c6c5/conditional_thresholds_with_product_keys.csv'
FIXTURE=ROOT+'runs/c26661067277af20/capacity_allocation_fixtures.csv'

def read(path):
    b=subprocess.check_output(['git','show',SHA+':'+path])
    return b,list(csv.DictReader(io.StringIO(b.decode())))

def main():
    mb,money=read(MONEY);fb,fixtures=read(FIXTURE)
    # Literal model inputs, explicitly hypothetical: one-way netfare8000,
    # per-journey paxcost500, constant residual gap500000, other-product seats80.
    candidates=[r for r in money if r['candidate']=='C01']
    # Obtain the exact field names from the published table without tolerating
    # a silent remapping of the fare/gap/customer unit.
    fare_key='net_fare_rub_per_oneway_journey'
    cost_key='variable_cost_rub_per_oneway_journey'
    gap_key='residual_funding_gap_rub'
    chosen=[r for r in candidates if Fraction(r[fare_key])==8000 and Fraction(r[cost_key])==500 and Fraction(r[gap_key])==500000]
    assert len(chosen)==1
    r=chosen[0]
    q=math.ceil(Fraction(500000,2*(8000-500)))
    fixture=next(r for r in fixtures if r['fixture']=='LOCAL_PLUS_TRANSFER')
    assert int(fixture['locals_each_leg'])==80 and int(fixture['nominal_seats_each_leg'])==100
    assert int(r['required_paid_journeys_each_direction'])==q
    # Four target physical legs (two outward/two return); each journey pays
    # once and consumes one seat on both legs in its direction.
    output=[]
    for reserve in [0,80]:
        capacity=100-reserve
        output.append(dict(candidate='C01',itinerary_template_id=r['itinerary_template_id'],net_fare_per_oneway_journey_rub=8000,variable_cost_per_oneway_journey_rub=500,residual_gap_rub=500000,required_customers_each_direction=q,total_oneway_journeys=2*q,physical_boardings=4*q,nominal_seats_each_leg=100,other_products_reserved_seats_each_leg=reserve,load_each_leg=reserve+q,capacity_remaining_each_direction=capacity,contribution_at_required_q_rub=2*q*(8000-500)-500000,contribution_at_capacity_rub=2*capacity*(8000-500)-500000,minimum_fare_if_q_equals_remaining_capacity_rub=str(Fraction(500000,2*capacity)+500),conditional_joint_capacity='PASS_SCENARIO'if q<=capacity else'FAIL_SCENARIO',value_status='SCENARIO',market_capacity='UNKNOWN',scope='Template only; equal reserves each of4legs. Not a real dated cohort or observed local bookings; no author arithmetic defect claimed.'))
    out=BASE/'reviews'/'conditional_capacity';out.mkdir(parents=True,exist_ok=True)
    with(out/'counterexample.csv').open('w',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(output[0]));w.writeheader();w.writerows(output)
    result=dict(source_sha=SHA,source_inputs=[dict(path=MONEY,sha256=hashlib.sha256(mb).hexdigest()),dict(path=FIXTURE,sha256=hashlib.sha256(fb).hexdigest())],required_q=q,other_seat_reserve=80,load_per_leg=114,remaining_q_capacity=20,threshold_margin_rub=10000,margin_at_reserved_capacity_rub=-200000,required_fare_at_capacity_rub=13000,scope='SCENARIO_COUNTEREXAMPLE_ONLY; author already limits threshold to nominal capacity; no actual reserve/cost/OD accepted',acceptance='PASS_MATH_FAIL_JOINT_CAPACITY_IN_THIS_SCENARIO')
    (out/'reproduction.json').write_text(json.dumps(result,indent=2)+'\n')
    lb,legs=read(ROOT+'runs/c26661067277af20/physical_legs.csv')
    reference=sorted([r for r in legs if r['variant']=='C07_reference'],key=lambda r:r['departure_utc'])
    chain=[r for r in legs if r['variant']=='C07_chain_turn30']
    reference_elapsed=int((dt.datetime.fromisoformat(reference[-1]['arrival_utc'])-dt.datetime.fromisoformat(reference[0]['departure_utc'])).total_seconds()/60)
    chain_blocks=sum(int(r['block_minutes'])for r in chain)
    assert chain_blocks==475 and reference_elapsed==255
    aircraft=dict(source_sha=SHA,source_path=ROOT+'runs/c26661067277af20/physical_legs.csv',sha256=hashlib.sha256(lb).hexdigest(),reference_elapsed_minutes=reference_elapsed,chain_blocks_only_lower_bound_minutes=chain_blocks,shortfall_even_with_zero_turn_minutes=chain_blocks-reference_elapsed,chain_elapsed_at_turn30_45_60=[chain_blocks+3*t for t in [30,45,60]],conditional_gate='FAIL_FIXED255MIN_WINDOW_UNDER_FROZEN_BLOCK_PROXIES',value_status='SCENARIO',actual_RW_blocks='UNKNOWN',actual_next_assignment='UNKNOWN',actual_donor='UNKNOWN',scope='Nonnegative ground time and fixed modeled first departure. Not an actual dispatch or donor feasibility verdict.')
    (out/'C07_deadline_bound.json').write_text(json.dumps(aircraft,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
