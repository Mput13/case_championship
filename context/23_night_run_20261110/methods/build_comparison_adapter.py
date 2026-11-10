#!/usr/bin/env python3
"""Map existing normalized tables and join bounded primary context to context21."""
import collections
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'runs/adapter_v1'
REPAIR=ROOT/'inputs/model-repair-001/proposed_common_view'
PRIMARY=ROOT/'inputs/primary-001'


def rows(path):
    with path.open(encoding='utf-8-sig',newline='')as f:return list(csv.DictReader(f))


def save(name,data):
    OUT.mkdir(parents=True,exist_ok=True)
    if name.endswith('.json'):
        (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    else:
        with (OUT/name).open('w',newline='')as f:
            w=csv.DictWriter(f,list(dict.fromkeys(k for r in data for k in r)));w.writeheader();w.writerows(data)


def near(a,b):assert abs(float(a)-float(b))<1e-6,(a,b)


def key(r):
    return r['model_id'],r['source_commit'],r['input_set_id'],r['run_id'],r['candidate_id'],r['profile'],r['scenario_id']


def qualify_flight_money(money, legs, summaries):
    """Fill omitted metadata by a unique full physical-flight reference, never name alone."""
    fields=['author_ref','input_set_id','run_id','mode','period_start','period_end','direction_scope',
            'market_unit','currency','price_basis','tax_basis','value_status','acceptance_scope']
    out=[];lineage=[]
    for i,row in enumerate(money,2):
        r=dict(row)
        if r['entry']=='flight_variable_cost':
            anchors=[l for l in legs if all(l[k]==r[k] for k in ['model_id','source_commit','candidate_id','profile','scenario_id','physical_leg_id'])]
            assert len(anchors)==1
            leg=anchors[0];summary=[s for s in summaries if key(s)==key(leg)]
            assert len(summary)==1
            filled=[]
            for field in fields:
                value=leg.get(field) or summary[0].get(field)
                assert value,('missing metadata',field,i)
                if r.get(field):assert r[field]==value
                else:r[field]=value;filled.append(field)
            lineage.append(dict(source_row=i,physical_leg_id=r['physical_leg_id'],candidate_id=r['candidate_id'],scenario_id=r['scenario_id'],
                                filled_fields=';'.join(filled),method='UNIQUE_PHYSICAL_LEG_THEN_EXACT_CONTEXT21_SUMMARY',amount_changed=False))
        out.append(r)
    return out,lineage


def validate_tables(its, links, legs, allocation, money, summaries):
    checks=[]
    groups={key(r)for r in its}
    for k in sorted(groups):
        ii=[r for r in its if key(r)==k];ll=[r for r in legs if key(r)==k]
        ix=[r for r in links if key(r)==k];aa=[r for r in allocation if key(r)==k]
        mm=[r for r in money if key(r)==k];rr=[r for r in summaries if key(r)==k]
        assert len(rr)==1
        im={r['itinerary_id']:r for r in ii};lm={r['physical_leg_id']:r for r in ll}
        assert len(im)==len(ii) and len(lm)==len(ll)
        assert {r['itinerary_id']for r in ix}==set(im)
        assert {r['physical_leg_id']for r in ix}==set(lm)
        assert {(r['itinerary_id'],r['sequence'],r['physical_leg_id'],r['seats'])for r in ix}=={(r['itinerary_id'],r['sequence'],r['physical_leg_id'],r['seats'])for r in aa}
        assert len(ix)==len(aa)==len({(r['itinerary_id'],r['sequence'])for r in ix})
        occup=collections.Counter()
        for itinerary_id,it in im.items():
            path=sorted([r for r in ix if r['itinerary_id']==itinerary_id],key=lambda r:int(r['sequence']))
            physical=[lm[r['physical_leg_id']]for r in path]
            assert [int(r['sequence'])for r in path]==list(range(1,len(path)+1))
            assert physical[0]['origin']==it['origin'] and physical[-1]['destination']==it['destination']
            for a,b in zip(physical,physical[1:]):
                assert a['destination']==b['origin'] and a['arrival_utc']<=b['departure_utc']
            near(float(it['trips'])*len(path),it['segments'])
            for r in path:
                near(r['seats'],it['trips']);occup[r['physical_leg_id']]+=float(r['seats'])
            gross=[r for r in mm if r['itinerary_id']==itinerary_id and r['entry']=='gross_revenue']
            assert len(gross)==1;near(gross[0]['amount_rub'],float(it['trips'])*float(it['fare_once']))
        for leg_id,leg in lm.items():
            near(occup[leg_id],leg['occupied']);assert occup[leg_id]<=float(leg['seats'])+1e-8
        fc=[r for r in mm if r['entry']=='flight_variable_cost']
        assert len(fc)==len(lm) and {r['physical_leg_id']for r in fc}==set(lm)
        for r in fc:near(r['amount_rub'],lm[r['physical_leg_id']]['flight_variable_cost_rub'])
        near(sum(float(r['flight_variable_cost_rub'])for r in ll),rr[0]['flight_variable_cost'])
        near(sum(float(r['amount_rub'])*float(r['sign_in_contribution'])for r in mm),rr[0]['contribution_before_base_fleet_opportunity'])
        checks.append(dict(candidate=k[4],profile=k[5],scenario=k[6],itineraries=len(ii),physical_legs=len(ll),status='PASS'))
    return checks


def main():
    its=rows(REPAIR/'itinerary.csv');links=rows(REPAIR/'itinerary_leg.csv')
    legs=rows(REPAIR/'physical_leg.csv');allocation=rows(REPAIR/'capacity_allocation.csv')
    money=rows(REPAIR/'money_ledger.csv');all_summaries=rows(REPAIR/'evaluation_summary.csv')
    summaries=[r for r in all_summaries if r['model_id']=='ciri_route_model']
    money,lineage=qualify_flight_money(money,legs,summaries)
    checks=validate_tables(its,links,legs,allocation,money,summaries)
    # These probes exercise semantic gates after parsing, not tampering with frozen files.
    probes=[]
    for label,bad_legs,bad_money in [
        ('missing_physical_leg',legs[1:],money),
        ('duplicate_physical_leg',legs+[legs[0]],money),
        ('per_leg_cost_shift',[dict(r,flight_variable_cost_rub=str(float(r['flight_variable_cost_rub'])+1000000)) if i==0 else r for i,r in enumerate(legs)],money),
        ('duplicate_flight_cost',legs,money+[next(r for r in money if r['entry']=='flight_variable_cost')])]:
        try:validate_tables(its,links,bad_legs,allocation,bad_money,summaries)
        except AssertionError:probes.append(dict(probe=label,status='REJECTED_AS_REQUIRED'))
        else:raise AssertionError('validator accepted mutation '+label)
    source_results=rows(ROOT/'inputs/set001/tsiri_93fa/context/21_team_proposals/comparison.csv')
    source_by={(r['network'],r['scenario']):r for r in source_results}
    coverage=rows(PRIMARY/'coverage.csv')
    cov={(r['origin'],r['destination'],r['period_start'],r['period_end']):r for r in coverage}
    assert len(cov)==len(coverage)
    joined=[];groups=collections.defaultdict(list)
    for r in rows(REPAIR/'market_pool.csv'):
        candidate=r['candidate_id'];sc=r['scenario_id'];a,b=r['market_id'].split('-')
        orig=source_by[candidate,sc]
        match=cov.get((a,b,r['period_start'],r['period_end']))
        j=dict(model_id=r['model_id'],source_commit=r['source_commit'],source_variant='context21_team_proposals',
               source_profile=orig['source_profile'],source_network=orig['source_network'],adapter_profile=r['profile'],
               input_set_id=r['input_set_id'],candidate_id=candidate,scenario_id=sc,origin=a,destination=b,
               period_start=r['period_start'],period_end=r['period_end'],scenario_D=r['D'],observed_endpoint_D=None,
               evidence_input_set='primary-001',evidence_commit='17b4f348f15ea8695688d9435933cb4965568408',
               publication_status=match['dated_evidence_status']if match else 'OUTSIDE_PRIMARY_COVERAGE_UNKNOWN',
               positive_source_cards=int(match['positive_source_cards'])if match else None,
               source_ids=match['source_ids']if match else None,
               no_card_means_no_service=False,own_and_other_carriers_may_both_be_present=True,
               demand_or_capacity_changed=False,source_acceptance='INDEPENDENT_SOURCE_JOIN_REVIEW_PENDING')
        flags={it['transfer']for it in its if it['candidate_id']==candidate and it['scenario_id']==sc and it['origin']==a and it['destination']==b}
        assert len(flags)==1
        j['itinerary_role']='TRANSFER_ENDPOINT'if flags=={'True'}else 'LOCAL_ENDPOINT'
        joined.append(j)
        if sc=='base':groups[candidate,j['itinerary_role']].append(j)
    coverage_summary=[]
    for (candidate,role),rs in sorted(groups.items()):
        coverage_summary.append(dict(candidate_id=candidate,variant='context21_team_proposals',role=role,
                                     directed_modeled_markets=len(rs),with_positive_publication=sum((r['positive_source_cards']or 0)>0 for r in rs),
                                     without_positive_publication_UNKNOWN=sum(not(r['positive_source_cards']or 0)>0 for r in rs),
                                     denominator='ACTUAL_EXPORTED_ITINERARY_ENDPOINTS_NOT_ALL_LEAF_COMBINATIONS',
                                     interpretation='PUBLICATION_CONTEXT_NOT_COMPETITOR_CAPACITY_OR_OBSERVED_DEMAND'))
    mapping=[]
    for table in ['candidate_register','parameter_registry','market_pool','itinerary','itinerary_leg','physical_leg','capacity_allocation','money_ledger','resource_ledger','evaluation_summary','source_manifest','findings','decision_ledger']:
        suffix='.json'if table in ['source_manifest','findings','decision_ledger']else '.csv'
        mapping.append(dict(table=table,path=str((REPAIR/(table+suffix)).relative_to(ROOT)),
                            input_set_id='model-repair-001',package_sha='27740ffea0821aa404ecd1013d1bb141613261f3',
                            variant='CONTEXT21_FOR_CIRI; ANASTASIA_AGGREGATES_SEPARATE',status='REUSE_PINNED_TABLE_WITH_EXPLICIT_NAMESPACE',
                            key_rule='model_id+source_commit+input_set_id+run_id+variant+profile+candidate+scenario; physical IDs additionally require candidate/profile context',
                            acceptance='MODEL_REPAIR_REVIEW_PENDING; METHODS_SEMANTIC_CHECKS_SCOPED'))
    mapping.append(dict(table='historical_candidate_register',path='inputs/data-bridge-001/normalized/candidate_register.csv',input_set_id='data-bridge-001',
                        package_sha='abc09bbb8e62d3513749b60b252d4521997acfc3',variant='CONDITIONAL16_FOR_CIRI',status='SEPARATE_HISTORICAL_SCENARIO_BRANCH',
                        key_rule='Never merge on model/candidate name alone; 860conditional16 !=224context21 itineraries',acceptance='SOURCE_JOIN_REVIEW_PENDING'))
    for m in mapping:
        if m['table']=='money_ledger':
            m['path']='runs/adapter_v1/qualified_money_ledger.csv'
            m['status']='160_FLIGHT_COST_ROWS_METADATA_QUALIFIED_BY_UNIQUE_LEG; AMOUNTS_UNCHANGED; ORIGINAL_RETAINED'
    bridges=[]
    for r in summaries:
        orig=source_by[r['candidate_id'],r['scenario_id']]
        for field in ['sold_journeys','segment_pax','gross_revenue','foregone_RW_revenue','flight_variable_cost','contribution_before_base_fleet_opportunity']:near(r[field],orig[field])
        bridges.append(dict(candidate_id=r['candidate_id'],scenario=r['scenario_id'],variant='context21_team_proposals',
                            original_source_profile=orig['source_profile'],original_source_network=orig['source_network'],repair_profile=r['profile'],
                            compatibility='NUMERIC_REPLAY_MATCHED_ON_SELECTED_OUTPUTS; PROFILE_PROVENANCE_RETAINED',
                            period='2026-12-07/13',currency='RUB',price_basis='CIRI_NET_SCENARIO',
                            money_definition='INCREMENTAL_CONTRIBUTION_BEFORE_FIXED_DONOR',full_budget=None,
                            contribution=float(r['contribution_before_base_fleet_opportunity'])))
    save('table_mapping.csv',mapping);save('semantic_checks.csv',checks);save('mutation_probes.csv',probes)
    save('qualified_money_ledger.csv',money);save('money_metadata_lineage.csv',lineage)
    save('market_publication_context.csv',joined);save('publication_coverage_summary.csv',coverage_summary);save('context21_replay_bridge.csv',bridges)
    save('status.json',dict(status='PASS_SCOPED_OWNER_ADAPTER_CHECKS',model_repair_review='PENDING',source_join_review='PENDING',
                            methods_review_v1='CHANGES_RETAINED_ON344f; F01_CURRENT_PROJECTION_PARENT_CLOSED; LEGACY_LABEL_HELD',
                            N01='NEW_ADAPTER_CHECKS_IDS_COSTS_AND_MUTATIONS; ORIGINAL_CHECKER_SCOPE_UNCHANGED',
                            N02='CORRECTED_METADATA_IMPORTED_WITH_ORIGINAL_VALUES_RETAINED; NOT_DISPATCH',
                            table_mappings=len(mapping),itineraries=len(its),leg_rows=len(legs),market_context_rows=len(joined),
                            annual_vs_weekly_money_join='PROHIBITED',conditional16_vs_context21_join='PROHIBITED_WITHOUT_VARIANT_MAPPING',
                            radius='OPEN_DECISION; NO_SCORE_SUM_ACROSS_DIFFERENT_CITY_SETS',
                            pool_excess_warning='model_repair author pool_excess_annual measures proposed Q(F) excess, not entire D; use common_market_bounds explicit fields',
                            no_new_capacity_or_demand=True))
    print(json.dumps(dict(cases=len(checks),mutation_probes=len(probes),market_context_rows=len(joined))))


if __name__=='__main__':main()
