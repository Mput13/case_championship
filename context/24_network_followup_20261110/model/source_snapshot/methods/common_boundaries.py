#!/usr/bin/env python3
"""Enumerate exact affine regions of the fixed greedy allocation rule.

Within a region each desired quantity, remaining seat count and migration cap
is affine in x. A minimum changes branch only at a root of two such lines.
The next region starts at the earliest positive crossing. No statistical model.
"""
import collections
import json
import math
import common_demand as m


def add(a,b):return a[0]+b[0],a[1]+b[1]
def sub(a,b):return a[0]-b[0],a[1]-b[1]
def mul(a,k):return a[0]*k,a[1]*k
def value(a,x):return a[0]+a[1]*x


def region(offers,cc,p,demands,x,end):
    events=[]
    def minimum(options):
        vals=[value(a,x) for a in options];low=min(vals)
        # Right derivative resolves ties at exact region boundary.
        candidate=min((a for a,v in zip(options,vals)if abs(v-low)<1e-7),key=lambda a:a[1])
        for a in options:
            d=sub(candidate,a)
            if abs(d[1])>1e-12:
                cross=-d[0]/d[1]
                if cross>x+1e-9 and cross<end:events.append(cross)
        return candidate
    caps={c['flight_id']:(float(c['capacity_scenario']),0)for c in cc}
    migration={(o['origin'],o['destination']):(o['known']or 0,0)for o in offers}
    total=(0,0);journeys=(0,0);segments=(0,0);transfers=(0,0)
    for o in offers:
        k=(o['origin'],o['destination'])
        desired=mul(demands[m.pair(*k)],o['coefficient'])
        sold=minimum([desired]+[caps[i]for i in o['legs']])
        for i in o['legs']:caps[i]=sub(caps[i],sold)
        direct=minimum([mul(sold,o['can']),migration[k]])
        migration[k]=sub(migration[k],direct)
        unknown=sub(mul(sold,o['can']),direct)
        margin=mul(sold,o['fare']-o['can']*o['oldfare']-len(o['legs'])*p['pax_cost'])
        margin=add(margin,mul(add(direct,mul(unknown,2)),p['pax_cost']))
        total=add(total,margin);journeys=add(journeys,sold);segments=add(segments,mul(sold,len(o['legs'])))
        if o['transfer']:transfers=add(transfers,sold)
    total=sub(total,(sum(float(c['flight_variable_cost'])for c in cc),0))
    return min(events,default=end),dict(contribution=total,journeys=journeys,segments=segments,transfers=transfers)


def trace(offers,cc,p,demands,end):
    x=0;pieces=[];verifications=0
    for _ in range(10000):
        right,aff=region(offers,cc,p,demands,x,end)
        assert right>x+1e-10,(x,right)
        for point in [x,(x+right)/2,right]:
            ds={k:value(a,point)for k,a in demands.items()}
            numerical,_,_=m.simulate(offers,cc,p,ds)
            for field,target in [('contribution','contribution_before_base_fleet_opportunity'),('journeys','sold_journeys'),('segments','segment_pax'),('transfers','transfer_journeys')]:
                m.near(value(aff[field],point),numerical[target],('piecewise confirmation',field,point),1e-5)
            verifications+=1
        pieces.append(dict(left=x,right=right,**{field+'_'+term:a[j]for field,a in aff.items()for j,term in enumerate(['intercept','slope'])}))
        x=right
        if x>=end-1e-10:return pieces,verifications
    raise AssertionError('region iteration cap')


def at(pieces,x,field='contribution'):
    p=next(p for p in pieces if p['left']-1e-8<=x<=p['right']+1e-8)
    return p[field+'_intercept']+p[field+'_slope']*x


def main():
    c=json.loads((m.ROOT/'common_demand_contract.json').read_text())
    summary=m.rows(m.SRC/'21_team_proposals/comparison.csv')
    sales=m.rows(m.SRC/'17_aircraft_route_review/model/sales.csv');caps=m.rows(m.SRC/'17_aircraft_route_review/model/capacity.csv')
    config=json.loads((m.SRC/'15_team_update/model/configuration.json').read_text())['scenarios']
    mapping=m.rows(m.OUT/'demand_mapping.csv');pieces=[];boundaries=[];curves={};checked=0
    for r in summary:
        n=r['network'];sc=r['scenario'];p=config[sc]
        ds=[x for x in mapping if x['network']==n and x['scenario']==sc]
        if not ds:continue
        C={tuple(x['pair'].split('-')):float(x['C_week_direction'])for x in ds}
        N={tuple(x['pair'].split('-')):float(x['N_week_direction_stress'])for x in ds}
        key=r['source_profile'],r['source_network'],sc
        ss=[s for s in sales if (s['profile'],s['network'],s['scenario'])==key]
        cc=[s for s in caps if (s['profile'],s['network'],s['scenario'])==key]
        offers=m.prepare(ss,cc,sc,p)
        capacities={s['flight_id']:float(s['capacity_scenario'])for s in cc}
        assert len([o for o in offers if not o['transfer']])==len(capacities)
        for recipe,ds0 in [('C',C),('N',N),('C_TO_N_BLEND',None)]:
            demands={k:(C[k],N[k]-C[k])if ds0 is None else (0,ds0[k])for k in C}
            end=1 if ds0 is None else max(capacities[o['legs'][0]]/(ds0[m.pair(o['origin'],o['destination'])]*o['coefficient'])for o in offers if not o['transfer'])
            trace_rows,v=trace(offers,cc,p,demands,end);checked+=v
            curves[n,sc,recipe]=trace_rows
            pieces.extend(dict(network=n,scenario=sc,recipe=recipe,**x)for x in trace_rows)
            roots=[]
            for x in trace_rows:
                if abs(x['contribution_slope'])>1e-10:
                    root=-x['contribution_intercept']/x['contribution_slope']
                    if x['left']-1e-9<=root<=x['right']+1e-9:roots.append(root)
            extrema=[(at(trace_rows,x),x)for x in {r['left']for r in trace_rows}|{end}]
            best,best_x=max(extrema)
            boundaries.append(dict(network=n,scenario=sc,recipe=recipe,domain_start=0,domain_end=end,
                                   region_count=len(trace_rows),zero_crossings=';'.join(format(x,'.12g')for x in sorted(set(round(x,10)for x in roots))),
                                   maximum_contribution=best,maximum_at=best_x,contribution_at_domain_end=at(trace_rows,end),
                                   after_domain='NOT_APPLICABLE_BLEND'if ds0 is None else 'CONSTANT_ALL_LOCAL_SEATS_FULL_TRANSFER0',
                                   full_budget_unknown=True,status='EXACT_FIXED_RULE_PIECEWISE_OWNER_VERIFIED'))
            if ds0 is not None:
                beyond,_,_=m.simulate(offers,cc,p,ds0,end*2)
                m.near(beyond['contribution_before_base_fleet_opportunity'],at(trace_rows,end),'saturation tail',1e-5)
                m.near(beyond['transfer_journeys'],0,'local full eliminates transfer')
    rank=[]
    for sc in ['base','cautious']:
        d=curves['D_SVX8',sc,'C_TO_N_BLEND'];h=curves['H_UFA_4',sc,'C_TO_N_BLEND']
        cuts=sorted({0.,1.}|{r['right']for r in d+h})
        for l,r in zip(cuts,cuts[1:]):
            dl=at(d,l)-at(h,l);dr=at(d,r)-at(h,r)
            if dl*dr<0:
                x=l-dl*(r-l)/(dr-dl)
                rank.append(dict(scenario=sc,candidate_a='D_SVX8',candidate_b='H_UFA_4',recipe='D(alpha)=(1-alpha)C+alphaN',
                                 alpha=x,contribution_a=at(d,x),contribution_b=at(h,x),
                                 interpretation='RANK_BOUNDARY_BEFORE_FIXED_COSTS; alpha_NOT_EMPIRICAL_OR_PROBABILITY',team_status='AGENT_PROPOSAL'))
    m.save('affine_regions.csv',pieces);m.save('exact_demand_boundaries.csv',boundaries);m.save('recipe_rank_boundaries.csv',rank)
    m.save('boundary_validation.json',dict(status='PASS_OWNER_PIECEWISE_AND_NUMERIC_CHECKS',region_count=len(pieces),point_checks=checked,
                                           scope='FIXED_GREEDY_ALLOCATION_AND_FARES_COSTS',independent_review='PENDING',global_network_optimum=False))
    print(json.dumps(dict(regions=len(pieces),checks=checked,rank_boundaries=rank)))


if __name__=='__main__':main()
