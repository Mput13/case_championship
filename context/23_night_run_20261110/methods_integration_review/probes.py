#!/usr/bin/env python3
"""Subject replay and adversarial probes, separate from independent oracle."""
import contextlib
import copy
import csv
import io
import json
from pathlib import Path
import shutil
import sys
import types
import oracle as o

SCRATCH=o.OUT/'.scratch'/'owner'
CAPTURE={}
PROBES=[]
MUTATION=None


def encode(name,data):
    if name.endswith('.json'):
        return (json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,list(dict.fromkeys(k for r in data for k in r)))
    writer.writeheader();writer.writerows(data);return stream.getvalue().encode()


def captured_rows(path):
    rel=str(path.relative_to(SCRATCH))
    b=CAPTURE.get(rel)
    if b is None:b=o.raw(rel)
    rs=list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
    return MUTATION(rel,rs) if MUTATION else rs


def captured_save(name,data):
    rel=str((m.OUT/name).relative_to(SCRATCH));CAPTURE[rel]=encode(name,data)


def module(name,relative):
    mod=types.ModuleType(name);mod.__file__=str(SCRATCH/relative);sys.modules[name]=mod
    exec(compile(o.raw(relative),relative,'exec'),mod.__dict__)
    return mod


def replay(target,expected_dir):
    global MUTATION
    MUTATION=None;CAPTURE.clear()
    with contextlib.redirect_stdout(io.StringIO()):target()
    result=[]
    for path,b in CAPTURE.items():
        if not path.startswith(expected_dir+'/'):continue
        expected=o.raw(path)
        assert b==expected,('replay byte mismatch',path)
        result.append(dict(path=path,byte_identical=True,bytes=len(b)))
    assert result
    return result


def rejected(name,fn,mutation=None):
    global MUTATION
    MUTATION=mutation;CAPTURE.clear()
    try:
        with contextlib.redirect_stdout(io.StringIO()):fn()
    except (AssertionError,KeyError,TypeError,ValueError) as e:
        PROBES.append(dict(name=name,status='REJECTED_BY_SUBJECT',error_type=type(e).__name__,error=str(e)[:500]))
    else:raise AssertionError(('mutation unexpectedly accepted',name))
    finally:MUTATION=None


def test(name,fn):
    with contextlib.redirect_stdout(io.StringIO()):evidence=fn()
    PROBES.append(dict(name=name,status='PASS',evidence=evidence))


def basic_offers(reverse=False,D=300,known=None):
    return [dict(origin='B' if reverse else 'A',destination='A' if reverse else 'B',legs=[('R' if reverse else 'F')+str(i)],
                 D=float(D),coefficient=.4,can=.8 if known is not None else 0,known=known,fare=100.,oldfare=90.,transfer=False,day=i+1) for i in range(4)]


def cap_for(offers,capacity=100):
    return [dict(flight_id=l,capacity_scenario=capacity,flight_variable_cost=0) for l in dict.fromkeys(l for x in offers for l in x['legs'])]


def shared_D():
    offers=basic_offers();caps=cap_for(offers)
    got,detail,left=m.simulate(offers,caps,dict(pax_cost=0),enforce_market_cap=True)
    o.near(got['sold_journeys'],300,'probe:hardD300')
    rejected('default_false_still_rejects_400_over_300',lambda:m.simulate(offers,caps,dict(pax_cost=0)))
    return dict(standalone_requested_after_leg_caps=400,shared_D=300,guard_sales=got['sold_journeys'],per_offer=[x['sold_journeys'] for x in detail],default_enforce_market_cap=False)


def signed_directions():
    offers=basic_offers()+basic_offers(True,D=150)
    got,detail,left=m.simulate(offers,cap_for(offers),dict(pax_cost=0),enforce_market_cap=True)
    f=sum(x['sold_journeys'] for x in detail if x['origin']=='A');r=sum(x['sold_journeys'] for x in detail if x['origin']=='B')
    o.near(f,300,'probe:forward');o.near(r,150,'probe:reverse');o.near(got['sold_journeys'],450,'probe:directions450')
    return dict(A_to_B=f,B_to_A=r,total=got['sold_journeys'],incorrect_undirected_cap_would=300)


def one_old_pool():
    offers=basic_offers(known=50);got,detail,left=m.simulate(offers,cap_for(offers),dict(pax_cost=10),enforce_market_cap=True)
    o.near(got['migrated_RW_direct'],50,'probe:old_seats_once')
    o.near(got['migrated_RW_total'],240,'probe:all_migration')
    o.near(got['saved_old_pax_variable'],(50+2*190)*10,'probe:old_cost_once')
    return dict(shared_known_old_seats=50,actual_direct_migration=got['migrated_RW_direct'],unverified_connecting=got['migrated_RW_unverified_connecting'],scope='Connecting migration remains source scenario, not observed recovery inventory')


def two_legs_one_fare():
    offers=[dict(origin='A',destination='C',legs=['L1','L2'],D=100,coefficient=1,can=0,known=None,fare=200,oldfare=200,transfer=True,day=1),
            dict(origin='A',destination='B',legs=['L1'],D=100,coefficient=1,can=0,known=None,fare=100,oldfare=100,transfer=False,day=1)]
    got,detail,left=m.simulate(offers,cap_for(offers),dict(pax_cost=5),enforce_market_cap=True)
    o.near(got['sold_journeys'],100,'probe:overlap_journeys');o.near(got['segment_pax'],200,'probe:two_seats');o.near(got['gross_revenue'],20000,'probe:one_through_fare');o.near(got['new_pax_variable'],1000,'probe:pax_per_segment')
    return dict(journeys=100,seat_segments=200,through_revenue_once=20000,second_offer_sold=detail[1]['sold_journeys'])


def union_cancel():
    journeys=[dict(legs=['L1','L2'],q=10,fare=100),dict(legs=['L2'],q=5,fare=60)]
    hit={'L1','L2'}
    proper=sum(x['q'] for x in journeys if hit.intersection(x['legs']));bad=sum(x['q']*len(hit.intersection(x['legs'])) for x in journeys)
    fare=sum(x['q']*x['fare'] for x in journeys if hit.intersection(x['legs']));badfare=sum(x['q']*x['fare']*len(hit.intersection(x['legs'])) for x in journeys)
    assert (proper,bad,fare,badfare)==(15,25,1300,2300)
    return dict(union_unserved=proper,wrong_leg_sum_unserved=bad,one_fare_loss=fare,wrong_leg_sum_fare=badfare)


def mutate_csv(relative,change):
    def mutate(path,rows):
        if path==relative:change(rows)
        return rows
    return mutate


def change_shared(field,value):
    def change(rs):
        # Any shared same-direction market in this singleton already repeats.
        sample=next(r for r in rs if r['profile']=='ROUTE_INPUTS_UPPER_100' and r['network']=='H_UFA_4' and r['scenario']=='base')
        sample[field]=value(sample[field])
    return mutate_csv(o.SRC+'17_aircraft_route_review/model/sales.csv',change)


def null_probe():
    global MUTATION
    target='inputs/cost-timebase-002/scenario_summary.csv'
    MUTATION=None;CAPTURE.clear()
    with contextlib.redirect_stdout(io.StringIO()):integration.main()
    baseline=CAPTURE['runs/kover_accounting_v1/context21_overlay.csv']
    def alter(rs):
        for r in rs:
            if r['network'].startswith('H_UFA') and r['scenario_id']=='delay_bank_next_day_fare_retained':
                r['hypothetical_overlay_delta_before_unknown_rub_if_recovered']='999999999'
                r['hypothetical_remaining_endpoint_journeys_if_recovered']='999999999'
    MUTATION=mutate_csv(target,alter);CAPTURE.clear()
    with contextlib.redirect_stdout(io.StringIO()):integration.main()
    assert baseline==CAPTURE['runs/kover_accounting_v1/context21_overlay.csv']
    MUTATION=None
    return dict(hypothetical_money_and_served_mutated_to=999999999,accepted_adapter_bytes_unchanged=True,held_rows=4)


def exact_input_boundary():
    """Expose exact-input scope, without requesting generalized validator work."""
    global MUTATION
    target='runs/common_demand_v1/itinerary_at_unit_scale.csv'
    def duplicate_N(rs):
        selected=next(r for r in rs if(r['network'],r['scenario'],r['recipe'])==('H_UFA_4','base','N'))
        rs.append(copy.deepcopy(selected))
    MUTATION=mutate_csv(target,duplicate_N);CAPTURE.clear()
    with contextlib.redirect_stdout(io.StringIO()):interaction.main()
    got=list(csv.DictReader(io.StringIO(CAPTURE['runs/kover_demand_v1/summary.csv'].decode())))
    original=o.rows('runs/kover_demand_v1/summary.csv')
    changed=[(r['candidate'],r['scenario'],r['recipe'],r['policy']) for r,s in zip(got,original) if r!=s]
    assert len(changed)==2 and all(k[:3]==('H_UFA_4','base','N') for k in changed)
    # Source identity + oracle uniqueness/hashes, not simulate(), protect this boundary.
    duplicate_rejected=False
    try:o.keyed(MUTATION(target,o.rows(target)),['network','scenario','recipe','multiplier','flight_ids'])
    except AssertionError:duplicate_rejected=True
    assert duplicate_rejected
    MUTATION=None
    return dict(owner_interaction_runtime_rejected=False,duplicate_itinerary_key_rejected_by_independent_oracle=True,
                changed_output_keys=changed,scope='Not a defect in the immutable pinned input; do not reuse exact-package approval as admission of a modified input_set')


def main():
    global m,portfolio,integration,interaction,MUTATION
    SCRATCH.mkdir(parents=True,exist_ok=True)
    # Only six small JSON documents are materialized. All CSVs stay in memory.
    for rel in ['common_demand_contract.json','portfolio_contract.json','portfolio_guard_contract.json','kover_demand_contract.json',
                o.SRC+'15_team_update/model/configuration.json','inputs/cost-kover-001/scenario_definitions.json']:
        p=SCRATCH/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(o.raw(rel))
    m=module('common_demand','common_demand.py');m.ROOT=SCRATCH;m.SRC=SCRATCH/o.SRC;m.OUT=SCRATCH/'runs/common_demand_v1';m.rows=captured_rows;m.save=captured_save
    portfolio=module('portfolio_comparison','portfolio_comparison.py')
    integration=module('integration_subject','integrate_kover_accounting.py')
    interaction=module('interaction_subject','kover_demand_interaction.py')
    guard=module('guard_subject','portfolio_guard_comparison.py')
    replays=[]
    for fn,where in [(m.main,'runs/common_demand_v1'),(integration.main,'runs/kover_accounting_v1'),(interaction.main,'runs/kover_demand_v1'),(portfolio.main,'runs/portfolio_v1_replay'),(guard.main,'runs/portfolio_v2')]:replays.extend(replay(fn,where))
    test('repeated_pair_hardD_400_to300',shared_D)
    test('signed_origin_destination_pools_are_distinct',signed_directions)
    test('one_shared_old_direct_seat_budget',one_old_pool)
    test('overlapping_legs_two_seats_one_through_fare',two_legs_one_fare)
    test('cancellation_union_not_sum_of_legs',union_cancel)
    inconsistent=basic_offers();inconsistent[1]['D']=301
    rejected('simulate_rejects_inconsistent_D_same_direction',lambda:m.simulate(inconsistent,cap_for(inconsistent),dict(pax_cost=0),enforce_market_cap=True))
    for field,value in [('D',lambda x:str(float(x)+1)),('fare_once',lambda x:str(float(x)+1)),('known_direct_RW_capacity',lambda x:'1' if x=='' else str(float(x)+1)),('transfer',lambda x:'False' if x=='True' else 'True')]:
        rejected('portfolio_shared_identity_'+field,lambda:portfolio.main(output_path=SCRATCH/'runs/probe'),change_shared(field,value))
    flights=o.SRC+'17_aircraft_route_review/model/flights.csv'
    def missing_flight(rs):
        victim=next(r for r in rs if r['profile']=='ROUTE_INPUTS_UPPER_100' and r['network']=='H_UFA_4');rs.remove(victim)
    rejected('interaction_missing_physical_id',interaction.main,mutate_csv(flights,missing_flight))
    caps=o.SRC+'17_aircraft_route_review/model/capacity.csv'
    def duplicate_capacity(rs):rs.append(copy.deepcopy(next(r for r in rs if r['profile']=='ROUTE_INPUTS_UPPER_100' and r['network']=='H_UFA_4' and r['scenario']=='base')))
    rejected('portfolio_duplicate_capacity',lambda:portfolio.main(output_path=SCRATCH/'runs/probe'),mutate_csv(caps,duplicate_capacity))
    corrected='inputs/cost-timebase-002/scenario_summary.csv'
    def bad_profile(rs):rs[0]['profile']='WRONG_PROFILE'
    rejected('adapter_wrong_source_profile',integration.main,mutate_csv(corrected,bad_profile))
    def delay_served_zero(rs):
        victim=next(r for r in rs if r['network']=='H_UFA_4' and r['scenario_id']=='delay_bank_next_day_fare_retained');victim['remaining_endpoint_journeys']='0'
    rejected('adapter_HOLD_served_NULL_to_zero',integration.main,mutate_csv(corrected,delay_served_zero))
    test('hypothetical_delay_money_never_accepted',null_probe)
    test('modified_input_requires_new_admission',exact_input_boundary)
    o.save('subject_replays.json',dict(status='PASS',files=replays,full_owner_algorithms_executed_for_comparison_only=True,independent_oracle='oracle.py'))
    o.save('adversarial_probes.json',dict(probes=PROBES,count=len(PROBES),owner_runtime_guard_is_not_general_input_admission=True))
    # Merge receipts from independent oracle and probes. Preserve deterministic order.
    previous=json.loads((o.OUT/'source_manifest.json').read_text())
    source={(x['commit'],x['path']):x for x in previous['sources']}
    source.update({(x['commit'],x['path']):x for x in o.RECEIPTS.values()})
    previous['sources']=sorted(source.values(),key=lambda x:(x['commit'],x['path']));o.save('source_manifest.json',previous)
    # No subprocess/server was launched; no open handles remain to this private scratch.
    assert SCRATCH.parent==o.OUT/'.scratch'
    shutil.rmtree(SCRATCH)
    SCRATCH.parent.rmdir()
    print(json.dumps(dict(status='PASS_SUBJECT_REPLAY_AND_ADVERSARIAL',replayed_files=len(replays),probes=len(PROBES))))


if __name__=='__main__':main()
