#!/usr/bin/env python3
"""Continuous fixed-offer allocation with explicit linearity and dual checks."""
import collections
import json
import math
import scipy
from scipy.optimize import linprog
import common_demand as m

OUT=m.ROOT/'runs/allocation_v1'


def main():
    contract=json.loads((m.ROOT/'allocation_contract.json').read_text())
    originals=m.rows(m.SRC/'21_team_proposals/comparison.csv')
    sales=m.rows(m.SRC/'17_aircraft_route_review/model/sales.csv')
    caps=m.rows(m.SRC/'17_aircraft_route_review/model/capacity.csv')
    cfg=json.loads((m.SRC/'15_team_update/model/configuration.json').read_text())['scenarios']
    mapping=m.rows(m.ROOT/'runs/common_demand_v1/demand_mapping.csv')
    accepted_bounds=m.rows(m.ROOT/'runs/budget_v1/supply_upper_bounds.csv')
    summaries=[];allocations=[];constraints=[];certificates=[];gates=[];baseline=[]
    cases=[]
    for r in originals:
        cases.append((r,'C',1.))
        if r['network']!='D_previous_best8':cases.append((r,'N',1.))
        if r['network']in ['H_UFA_4','H_UFA_8']and r['scenario']=='base':cases.append((r,'C',3.))
    assert len(cases)==16
    for r,recipe,scale in cases:
        n,sc=r['network'],r['scenario'];case=n+'|'+sc+'|'+recipe+'|'+str(scale);p=cfg[sc]
        ss=[s for s in sales if(s['profile'],s['network'],s['scenario'])==(r['source_profile'],r['source_network'],sc)]
        cc=[c for c in caps if(c['profile'],c['network'],c['scenario'])==(r['source_profile'],r['source_network'],sc)]
        offers=m.prepare(ss,cc,sc,p)
        demand=None if recipe=='C'else {tuple(x['pair'].split('-')):float(x['N_week_direction_stress'])for x in mapping if x['network']==n and x['scenario']==sc}
        desired=[];D={};market=collections.defaultdict(list);legcaps={c['flight_id']:float(c['capacity_scenario'])for c in cc}
        for i,o in enumerate(offers):
            k=o['origin'],o['destination'];market[k].append(i)
            d=(o['D']if demand is None else demand[m.pair(*k)])*scale;D[k]=d;desired.append(d*o['coefficient'])
        oldsegments={}
        for k,indices in market.items():
            known={offers[i]['known']for i in indices};can={offers[i]['can']for i in indices}
            assert len(known)==len(can)==1
            known=known.pop();can=can.pop()
            upper=sum(min(desired[i],*(legcaps[l]for l in offers[i]['legs']))for i in indices)
            if known is None or known==0:kold=2
            else:
                assert can*upper<=known+1e-7,('binding migration kink; LP held',case,k,can*upper,known)
                kold=1
            oldsegments[k]=kold
            gates.append(dict(case_id=case,origin=k[0],destination=k[1],known_own_cap=known,can=can,
                              optimistic_possible_sales=upper,can_times_sales_upper=can*upper,old_segments_per_migrated=kold,
                              status='LINEAR_ON_ENTIRE_FEASIBLE_SET_NOT_ONLY_LOCAL_FIRST'))
        w=[o['fare']-o['can']*o['oldfare']-len(o['legs'])*p['pax_cost']+o['can']*oldsegments[o['origin'],o['destination']]*p['pax_cost']for o in offers]
        A=[];b=[];labels=[]
        for leg,cap in legcaps.items():A.append([int(leg in o['legs'])for o in offers]);b.append(cap);labels.append('LEG|'+leg)
        for k,indices in market.items():A.append([int(i in indices)for i in range(len(offers))]);b.append(D[k]);labels.append('OD|'+'-'.join(k))
        reference,rr,_=m.simulate(offers,cc,p,demand,scale)
        refmap={x['flight_ids']:x for x in rr}
        assert len(refmap)==len(rr)==len(offers)
        x0=[refmap[';'.join(o['legs'])]['sold_journeys']for o in offers]
        cost=sum(float(c['flight_variable_cost'])for c in cc)
        m.near(sum(a*x for a,x in zip(w,x0))-cost,reference['contribution_before_base_fleet_opportunity'],'linear migration accounting',1e-5)
        baseline.append(dict(case_id=case,local_first_contribution=reference['contribution_before_base_fleet_opportunity'],
                             local_first_journeys=reference['sold_journeys'],local_first_segments=reference['segment_pax'],
                             local_first_transfers=reference['transfer_journeys']))
        goals={'CONTRIBUTION':w,'ENDPOINT_JOURNEYS':[1.]*len(offers),'PASSENGER_SEGMENTS':[float(len(o['legs']))for o in offers]}
        for objective,v in goals.items():
            lp=linprog([-x for x in v],A_ub=A,b_ub=b,bounds=list(zip([0.]*len(offers),desired)),method='highs')
            assert lp.success,(case,objective,lp.message)
            optimum=-float(lp.fun);dual=[-float(x)for x in lp.ineqlin.marginals];mu=[-float(x)for x in lp.upper.marginals]
            assert min(dual+mu)>=-1e-7
            dual_value=sum(a*x for a,x in zip(b,dual))+sum(a*x for a,x in zip(desired,mu))
            m.near(optimum,dual_value,'primary objective strong dual certificate',1e-5)
            for i,o in enumerate(offers):
                gap=sum(A[j][i]*dual[j]for j in range(len(A)))+mu[i]-v[i]
                assert gap>=-1e-6,(case,objective,i,gap)
                certificates.append(dict(case_id=case,objective=objective,offer=i,objective_coefficient=v[i],
                                         sum_constraint_shadow=sum(A[j][i]*dual[j]for j in range(len(A))),
                                         offer_upper_shadow=mu[i],dual_slack=gap,desired=desired[i]))
            for label,rhs,shadow in zip(labels,b,dual):constraints.append(dict(case_id=case,objective=objective,constraint=label,rhs=rhs,shadow=shadow))
            # Primary profit is already deterministic enough for an accounting
            # comparison. Other objectives use profit only after their optimum.
            tie_dual_value=None
            if objective!='CONTRIBUTION':
                tie=linprog([-x for x in w],A_ub=A+[[-x for x in v]],b_ub=b+[-optimum+1e-8],
                            bounds=list(zip([0.]*len(offers),desired)),method='highs')
                assert tie.success,(case,objective,tie.message)
                x=[float(z)for z in tie.x]
                td=[-float(z)for z in tie.ineqlin.marginals];tm=[-float(z)for z in tie.upper.marginals]
                assert min(td+tm)>=-1e-7
                tie_dual_value=sum(a*z for a,z in zip(b+[-optimum+1e-8],td))+sum(a*z for a,z in zip(desired,tm))
                m.near(-float(tie.fun),tie_dual_value,'secondary profit strong duality',1e-5)
                for i in range(len(offers)):
                    assert sum(A[j][i]*td[j]for j in range(len(A)))-v[i]*td[-1]+tm[i]-w[i]>=-1e-6
            else:x=[float(z)for z in lp.x]
            assert all(-1e-7<=z<=upper+1e-7 for z,upper in zip(x,desired))
            assert all(sum(a*z for a,z in zip(row,x))<=rhs+1e-6 for row,rhs in zip(A,b))
            actual_objective=sum(a*z for a,z in zip(v,x));ref_objective=sum(a*z for a,z in zip(v,x0))
            assert actual_objective>=optimum-1e-5 and actual_objective>=ref_objective-1e-5
            total=collections.Counter()
            for i,(o,z)in enumerate(zip(offers,x)):
                k=o['origin'],o['destination'];count=len(o['legs']);old=oldsegments[k]
                values=dict(journeys=z,segments=count*z,transfers=z if o['transfer']else 0,
                            own_migrated_journeys=z*o['can'],net_new_RW_journeys=z*(1-o['can']),
                            gross=z*o['fare'],foregone=z*o['can']*o['oldfare'],new_pax=z*count*p['pax_cost'],
                            saved_old_pax=z*o['can']*old*p['pax_cost'])
                total.update(values)
                allocations.append(dict(case_id=case,objective=objective,origin=k[0],destination=k[1],flight_ids=';'.join(o['legs']),
                                        desired=desired[i],local_first_sold=x0[i],allocated=z,unit_incremental_margin=w[i],**values))
            contribution=total['gross']-total['foregone']-cost-total['new_pax']+total['saved_old_pax']
            m.near(contribution,sum(z*a for z,a in zip(x,w))-cost,'accounting check',1e-5)
            upper=next(float(z['optimistic_contribution_upper'])for z in accepted_bounds if z['network']==n and z['scenario']==sc)
            assert contribution<=upper+1e-5
            summaries.append(dict(case_id=case,candidate=n,scenario=sc,recipe=recipe,scale=scale,objective=objective,
                                   primary_optimum=optimum,primary_dual_certificate=dual_value,primary_achieved=actual_objective,
                                   secondary_profit_dual_before_flight_cost=tie_dual_value,
                                   contribution=contribution,journeys=total['journeys'],segments=total['segments'],transfers=total['transfers'],
                                   own_migrated_journeys=total['own_migrated_journeys'],net_new_RW_journeys=total['net_new_RW_journeys'],
                                   local_first_contribution=reference['contribution_before_base_fleet_opportunity'],
                                   contribution_delta_vs_local_first=contribution-reference['contribution_before_base_fleet_opportunity'],
                                   supply_upper_bound=upper,active_allocated=r['active_allocated'],full_budget=None,
                                   status='CONTINUOUS_FIXED_OFFER_OPTIMUM_ONLY; OBJECTIVE_NOT_TEAM_ACCEPTED',independent_review='PENDING'))
    old=m.OUT
    try:
        m.OUT=OUT;m.save('summary.csv',summaries);m.save('allocations.csv',allocations);m.save('constraint_duals.csv',constraints)
        m.save('offer_dual_certificates.csv',certificates);m.save('migration_linearity_gates.csv',gates);m.save('local_first_reference.csv',baseline)
        m.save('validation.json',dict(status='PASS_OWNER_PRIMAL_DUAL_AND_ACCOUNTING',case_count=len(cases),objective_cases=len(summaries),
                                      primary_dual_certificates=48,secondary_profit_dual_checks=32,
                                      scipy=scipy.__version__,solver='HiGHS through scipy.linprog',new_dependency_install=False,
                                      independent_review='PENDING_NEW_ALLOCATION_SCOPE',global_network_optimum=False,
                                      observed_demand=False,full_budget=False,integer_booking_assignment=False))
    finally:m.OUT=old
    print(json.dumps(dict(cases=len(cases),objectives=len(summaries),max_profit_gain=max(r['contribution_delta_vs_local_first']for r in summaries if r['objective']=='CONTRIBUTION'))))


if __name__=='__main__':main()
