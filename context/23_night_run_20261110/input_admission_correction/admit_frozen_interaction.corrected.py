#!/usr/bin/env python3
"""Read-only admission of the exact MR11 input, not approval of new inputs."""
import collections
import copy
import csv
import hashlib
import io
import json
import math
import subprocess
from decimal import Decimal
import common_demand as m

SUBJECT='f7a034dc91917cc69c5f8b3a729c3d1c6dfeb5b9'
SALES='runs/common_demand_v1/itinerary_at_unit_scale.csv'
SUMMARY='runs/common_demand_v1/summary.csv'
FLIGHTS='inputs/set001/tsiri_93fa/context/17_aircraft_route_review/model/flights.csv'
CAPACITY='inputs/set001/tsiri_93fa/context/17_aircraft_route_review/model/capacity.csv'
CONTEXT=['experiment_id','source_commit','source_variant','source_profile','source_network','input_set_id','period_start','period_end','price_basis','tax_basis']
SUM_FIELDS=['sold_journeys','transfer_journeys','segment_pax','migrated_RW_total','migrated_RW_direct','migrated_RW_unverified_connecting','gross_revenue','foregone_RW_revenue','new_pax_variable','saved_old_pax_variable']


def parse(data):return list(csv.DictReader(io.StringIO(data.decode())))
def group(r):return r['network'],r['scenario'],r['recipe'],Decimal(r['multiplier'])
def key(r):return group(r)+(r['origin'],r['destination'],tuple(r['flight_ids'].split(';')))
def require(ok,code):
    if not ok:raise ValueError(code)
def close(a,b,code):require(math.isfinite(float(a))and math.isfinite(float(b))and abs(float(a)-float(b))<=1e-5,code)
def verify_bytes(actual,frozen):require(actual==frozen,'IMMUTABLE_HASH_DRIFT_REQUIRES_NEW_INPUT_SET_AND_ORACLE')


def validate(rows,reference_keys,summary,flights,capacity,oracle):
    keys=[key(r)for r in rows]
    require(len(keys)==len(set(keys)),'DUPLICATE_ITINERARY_KEY')
    require(set(keys)==reference_keys,'ITINERARY_KEY_SET_DRIFT')
    unit_summary=[r for r in summary if Decimal(r['multiplier'])==1]
    summaries={group(r):r for r in unit_summary}
    require(len(summaries)==len(unit_summary),'DUPLICATE_UNIT_SUMMARY_KEY')
    require(len(summaries)==12,'SUMMARY_KEY_DRIFT')
    grouped=collections.defaultdict(list)
    for r in rows:grouped[group(r)].append(r)
    require(set(grouped)==set(summaries),'SUMMARY_GROUP_COVERAGE')
    affected={}
    for g,ss in grouped.items():
        expected=summaries[g]
        for s in ss:
            require(all(s[c]==expected[c]for c in CONTEXT),'CONTEXT_DRIFT')
            require(s['recipe']in ['C','N']and Decimal(s['multiplier'])==1,'INPUT_RECIPE_SCOPE')
            q=float(s['sold_journeys']);ids=s['flight_ids'].split(';')
            require(q>=0 and q<=float(s['desired'])+1e-7,'DESIRED_QUANTITY_BOUND')
            close(q*float(s['fare_once']),s['gross_revenue'],'ONE_FARE_IDENTITY')
            close(q*len(ids),s['segment_pax'],'JOURNEY_SEGMENT_IDENTITY')
            close(float(s['migrated_RW_direct'])+float(s['migrated_RW_unverified_connecting']),s['migrated_RW_total'],'OWN_MIGRATION_IDENTITY')
        ff=[f for f in flights if(f['profile'],f['network'])==(expected['source_profile'],expected['source_network'])]
        fmap={f['id']:f for f in ff};require(len(fmap)==len(ff),'DUPLICATE_SOURCE_FLIGHT')
        cc=[c for c in capacity if(c['profile'],c['network'],c['scenario'])==(expected['source_profile'],expected['source_network'],g[1])]
        cmap={c['flight_id']:c for c in cc};require(len(cmap)==len(cc),'DUPLICATE_CAPACITY')
        require(set(fmap)==set(cmap)=={i for s in ss for i in s['flight_ids'].split(';')},'FULL_FLIGHT_CAPACITY_ID_SET')
        occupied=collections.Counter();markets=collections.defaultdict(list)
        touched={f['id']for f in ff if(f['origin']=='UFA'and 0<=float(f['departure_utc_minute'])<1440)or(f['destination']=='UFA'and 0<=float(f['arrival_utc_minute'])<1440)}
        for s in ss:
            ids=s['flight_ids'].split(';');legs=[fmap[i]for i in ids]
            require(legs[0]['origin']==s['origin']and legs[-1]['destination']==s['destination'],'ENDPOINT_KEY')
            require(all(a['destination']==b['origin']for a,b in zip(legs,legs[1:])),'ITINERARY_CONTINUITY')
            for i in ids:occupied[i]+=float(s['sold_journeys'])
            markets[s['origin'],s['destination']].append(s)
            if touched.intersection(ids):
                ak=g[:3]+(s['flight_ids'],);require(ak not in affected,'DUPLICATE_AFFECTED_KEY')
                affected[ak]=(float(s['sold_journeys']),float(s['fare_once']),float(s['gross_revenue']),len(touched.intersection(ids)))
        for i,c in cmap.items():require(occupied[i]<=float(c['capacity_scenario'])+1e-7,'LEG_CAPACITY')
        for market in markets.values():
            ds={float(s['D'])for s in market};require(len(ds)==1,'MARKET_D_CONFLICT')
            require(sum(float(s['sold_journeys'])for s in market)<=ds.pop()+1e-7,'DIRECTED_MARKET_BOUND')
        for field in SUM_FIELDS:close(sum(float(s[field])for s in ss),expected[field],'SUMMARY_'+field)
        close(sum(float(c['flight_variable_cost'])for c in cc),expected['flight_variable_cost'],'ONE_FLIGHT_COST_SUM')
    oracle_map={(r['candidate'],r['scenario'],r['recipe'],r['flight_ids']):r for r in oracle}
    require(len(oracle_map)==len(oracle)==160,'INDEPENDENT_ORACLE_KEY')
    require(set(affected)==set(oracle_map),'INDEPENDENT_AFFECTED_KEY_SET')
    for k,actual in affected.items():
        r=oracle_map[k]
        for got,name in zip(actual,['journeys','fare_once','lost_fare_once','affected_leg_count']):close(got,r[name],'INDEPENDENT_AFFECTED_ORACLE')
    return dict(unique_itineraries=len(keys),summary_groups=len(grouped),independent_affected_rows=len(affected))


def main():
    files={};receipts=[]
    for name in [SALES,SUMMARY,FLIGHTS,CAPACITY]:
        path=m.ROOT/name;source_path=str(path.relative_to(m.ROOT.parents[2]))
        frozen=subprocess.check_output(['git','show',SUBJECT+':'+source_path],cwd=m.ROOT.parents[2])
        actual=path.read_bytes()
        verify_bytes(actual,frozen)
        files[name]=parse(actual)
        receipts.append(dict(path=name,subject_commit=SUBJECT,sha256=hashlib.sha256(actual).hexdigest()))
    rows=files[SALES];reference_keys={key(r)for r in rows}
    oracle=m.rows(m.ROOT/'inputs/integration-oracle-001/independent_affected_itinerary.csv')
    # Oracle bytes themselves must equal the independent pinned review.
    receipt_bytes=(m.ROOT/'inputs/integration-oracle-001/receipt.json').read_bytes()
    require(hashlib.sha256(receipt_bytes).hexdigest()=='8373a8085682cc9df3660433f8024a78a377f9b512c93d05ecaafbc9a71d2db6','ORACLE_RECEIPT_DRIFT_REQUIRES_NEW_REVIEW')
    receipt=json.loads(receipt_bytes)
    for f in receipt['files']:require(hashlib.sha256((m.ROOT/f['path']).read_bytes()).hexdigest()==f['sha256'],'ORACLE_HASH_DRIFT')
    args=files[SUMMARY],files[FLIGHTS],files[CAPACITY],oracle
    passed=validate(rows,reference_keys,*args);probes=[]
    i=next(i for i,r in enumerate(rows)if(r['network'],r['scenario'],r['recipe'])==('H_UFA_4','base','N'))
    mutations=[]
    duplicate=copy.deepcopy(rows);duplicate.append(copy.deepcopy(rows[i]));mutations.append(('duplicate_N_itinerary',duplicate,'DUPLICATE_ITINERARY_KEY'))
    missing=copy.deepcopy(rows);missing.pop(i);mutations.append(('missing_N_itinerary',missing,'ITINERARY_KEY_SET_DRIFT'))
    amount=copy.deepcopy(rows);amount[i]['gross_revenue']=str(float(amount[i]['gross_revenue'])+1);mutations.append(('changed_N_fare_total',amount,'ONE_FARE_IDENTITY'))
    context=copy.deepcopy(rows);context[i]['source_profile']='WRONG_PROFILE';mutations.append(('changed_profile',context,'CONTEXT_DRIFT'))
    for name,mutant,expected in mutations:
        try:validate(mutant,reference_keys,*args)
        except ValueError as e:require(str(e)==expected,('WRONG_MUTATION_REJECTION',name,str(e)));probes.append(dict(probe=name,status='REJECTED',reason=str(e)))
        else:raise AssertionError(('MUTATION_NOT_REJECTED',name))
    try:verify_bytes((m.ROOT/SALES).read_bytes()+b'\n',(m.ROOT/SALES).read_bytes())
    except ValueError as e:probes.append(dict(probe='changed_bytes_without_new_admission',status='REJECTED',reason=str(e)))
    else:raise AssertionError('HASH_MUTATION_NOT_REJECTED')
    changed_oracle=copy.deepcopy(oracle);changed_oracle[0]['journeys']=str(float(changed_oracle[0]['journeys'])+1)
    try:validate(rows,reference_keys,files[SUMMARY],files[FLIGHTS],files[CAPACITY],changed_oracle)
    except ValueError as e:
        require(str(e)=='INDEPENDENT_AFFECTED_ORACLE','WRONG_ORACLE_REJECTION')
        probes.append(dict(probe='key_preserved_but_oracle_quantity_changed',status='REJECTED',reason=str(e)))
    else:raise AssertionError('ORACLE_MUTATION_NOT_REJECTED')
    summary_duplicate=copy.deepcopy(files[SUMMARY]);summary_duplicate.append(copy.deepcopy(next(r for r in summary_duplicate if Decimal(r['multiplier'])==1)))
    try:validate(rows,reference_keys,summary_duplicate,files[FLIGHTS],files[CAPACITY],oracle)
    except ValueError as e:
        require(str(e)=='DUPLICATE_UNIT_SUMMARY_KEY','WRONG_SUMMARY_REJECTION')
        probes.append(dict(probe='duplicate_unit_summary',status='REJECTED',reason=str(e)))
    else:raise AssertionError('SUMMARY_DUPLICATE_NOT_REJECTED')
    old=m.OUT
    try:
        m.OUT=m.ROOT/'runs/input_admission_v1';m.save('input_receipt.json',dict(subject_commit=SUBJECT,files=receipts))
        m.save('mutation_checks.json',probes);m.save('checks.json',dict(status='PASS_OWNER_READ_ONLY_ADMISSION_OF_EXACT_MR11_INPUT',**passed,
                   independent_oracle_commit='ea2a9626aef75c121f2da7d778b47edce0d571b7',new_inputs_accepted=False,
                   old_interaction_code_changed=False,old_calculations_changed=False,independent_review_of_new_guard='PENDING'))
    finally:m.OUT=old


if __name__=='__main__':main()
