#!/usr/bin/env python3
"""Explicit finite portfolios; shared markets, dated resources, one own-seat pool."""
import collections
import itertools
import json
import math
import common_demand as m

OUT=m.ROOT/'runs/portfolio_v1'


def dump(name,data):
    old=m.OUT
    try:m.OUT=OUT;m.save(name,data)
    finally:m.OUT=old


def main():
    contract=json.loads((m.ROOT/'portfolio_contract.json').read_text())
    rs=m.rows(m.SRC/'21_team_proposals/comparison.csv')
    allsales=m.rows(m.SRC/'17_aircraft_route_review/model/sales.csv')
    allcaps=m.rows(m.SRC/'17_aircraft_route_review/model/capacity.csv')
    allflights=m.rows(m.SRC/'17_aircraft_route_review/model/flights.csv')
    config=json.loads((m.SRC/'15_team_update/model/configuration.json').read_text())['scenarios']
    candidates=sorted({r['network']for r in rs});source={};calendar=[]
    for r in rs:
        n,sc=r['network'],r['scenario'];key=r['source_profile'],r['source_network']
        ss=[dict(s)for s in allsales if (s['profile'],s['network'],s['scenario'])==(*key,sc)]
        cc=[dict(s)for s in allcaps if (s['profile'],s['network'],s['scenario'])==(*key,sc)]
        ff=[dict(s)for s in allflights if (s['profile'],s['network'])==key]
        for s in ss:s['flight_ids']=';'.join(n+'|'+i for i in s['flight_ids'].split(';'))
        for c in cc:c['flight_id']=n+'|'+c['flight_id']
        fmap={n+'|'+f['id']:f for f in ff}
        assert {c['flight_id']for c in cc}==set(fmap)
        for tail in {f['aircraft']for f in ff}:
            fs=sorted([f for f in ff if f['aircraft']==tail],key=lambda f:float(f['departure_utc_minute']))
            gaps=[]
            for a,b in zip(fs,fs[1:]):
                assert a['destination']==b['origin'],('tail discontinuity',n,tail,a,b)
                gap=float(b['departure_utc_minute'])-float(a['arrival_utc_minute'])
                assert gap>=45,('tail turn',n,tail,gap)
                gaps.append(gap)
            calendar.append(dict(network=n,scenario=sc,tail_namespace=n+'|'+tail,legs=len(fs),minimum_turn_minutes=min(gaps)if gaps else None,
                                 status='SOURCE_CALENDAR_CONTINUITY_AND45MIN_PASS_NOT_DISPATCH'))
        assert len({f['aircraft']for f in ff})==int(r['active_allocated'])
        source[n,sc]=r,ss,cc,fmap
    results=[];market_audit=[];detail=[];validation=[]
    for count in range(1,5):
        for subset in itertools.combinations(candidates,count):
            pid='+'.join(subset)
            for sc in ['base','cautious']:
                parts=[source[n,sc]for n in subset];p=config[sc]
                ss=[s for _,sales,_,_ in parts for s in sales];cc=[c for _,_,caps,_ in parts for c in caps]
                fmap={k:v for _,_,_,fs in parts for k,v in fs.items()}
                assert len(fmap)==len(cc)==len({c['flight_id']for c in cc})
                grouped=collections.defaultdict(list)
                for s in ss:grouped[s['origin'],s['destination']].append(s)
                for k,group in grouped.items():
                    for field in ['D','fare_once','transfer','known_direct_RW_capacity']:
                        assert len({s[field]for s in group})==1,('incompatible shared field',pid,k,field)
                working=sum(int(r['active_allocated'])for r,_,_,_ in parts)
                additive=sum(float(r['contribution_before_base_fleet_opportunity'])for r,_,_,_ in parts)
                for law in contract['capture_laws']:
                    law=law.split(':')[0]
                    offers=m.prepare(ss,cc,sc,p)
                    temporal={k:len({(fmap[s['flight_ids'].split(';')[0]]['date'],fmap[s['flight_ids'].split(';')[0]]['departure_utc_minute'])for s in g})for k,g in grouped.items()}
                    if law=='COUNT_DISTINCT_DEPARTURE_TIMES':
                        for o in offers:
                            k=o['origin'],o['destination'];f=temporal[k]
                            o['coefficient']=(.45 if sc=='base'else .30)*(1-math.exp(-f/3))*(.65 if o['transfer']else 1)/len(grouped[k])
                    total,dd,remaining=m.simulate(offers,cc,p)
                    if len(subset)==1:
                        for field in ['sold_journeys','segment_pax','migrated_RW_total','gross_revenue','foregone_RW_revenue','saved_old_pax_variable','contribution_before_base_fleet_opportunity']:
                            m.near(total[field],parts[0][0][field],('singleton',pid,law,field))
                    meta=dict(portfolio=pid,scenario=sc,capture_law=law,mode='COMMON_COMPARISON',input_set_id=contract['id'],variant='context21_team_proposals',
                              working_required=working,reserve_assumption=1,current4_working_ceiling_pass=working<=4,
                              extra_working_above4=max(0,working-4),new_UFA_base_count=int(any(n.startswith('H_UFA')for n in subset)),
                              resource_status='WITHIN_MODELED4PLUS1_CEILING'if working<=4 else 'CONDITIONAL_LARGER_RESOURCE_ENVELOPE_NOT_CONFIRMED_FUTURE_FLEET',
                              numerical_price_period='CIRI_NET_RUB_WEEK_20261207_13',full_budget=None,decision_status='AGENT_PROPOSAL')
                    results.append(dict(**meta,**total,additive_component_contribution=additive,delta_vs_additive=total['contribution_before_base_fleet_opportunity']-additive))
                    for k,group in grouped.items():
                        sold=[x for x in dd if (x['origin'],x['destination'])==k]
                        oldsum=sum(float(s['sold_journeys'])for s in group);newsum=sum(s['sold_journeys']for s in sold);D=float(group[0]['D'])
                        directcaps={float(s['known_direct_RW_capacity'])for s in group if s['known_direct_RW_capacity']}
                        assert len(directcaps)<=1
                        if directcaps:assert sum(x['migrated_RW_direct']for x in sold)<=next(iter(directcaps))+1e-8
                        assert newsum<=D+1e-8
                        if len({s['flight_ids'].split('|')[0]for s in group})>1:
                            market_audit.append(dict(**meta,origin=k[0],destination=k[1],D=D,offered_itineraries=len(group),distinct_departure_times=temporal[k],
                                                     additive_sold=oldsum,pooled_sold=newsum,additive_exceeds_entire_D=oldsum>D+1e-8,
                                                     pooled_exceeds_entire_D=False,own_direct_cap_counted_once=True))
                    if len(subset)==2:
                        detail.extend(dict(**meta,**x)for x in dd)
                    validation.append(dict(portfolio=pid,scenario=sc,capture_law=law,itineraries=len(dd),legs=len(cc),status='PASS_CAPACITY_MARKET_OWN_CAP_AND_COST_ACCOUNTING'))
    dump('summary.csv',results);dump('shared_market_audit.csv',market_audit);dump('pair_portfolio_itineraries.csv',detail)
    dump('calendar_checks.csv',calendar);dump('case_checks.csv',validation)
    dump('validation.json',dict(status='PASS_OWNER_CHECKS',cases=len(results),singleton_cases=16,portfolio_subsets=15,
                                current_ceiling_cases=sum(r['current4_working_ceiling_pass']for r in results),
                                independent_review='PENDING',new_global_optimum=False,observed_demand=False,future_fleet_confirmed=False))
    print(json.dumps(dict(cases=len(results),shared_market_records=len(market_audit))))


if __name__=='__main__':main()
