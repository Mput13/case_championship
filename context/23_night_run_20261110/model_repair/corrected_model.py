#!/usr/bin/env python3
"""Shared-pair correction for Anastasia's frozen network_model (AGENT_PROPOSAL).

Units inherited explicitly: weekly ONE-DIRECTION scenario journeys; symmetric
return service, annual both-direction quantities = weekly * 2 * weeks. Source
segment demand is only a scenario proxy for endpoint journeys. No observed OD.

Triangle frequencies retain the author's standalone frequency rule. Selection
re-evaluates the whole network's capture at SUM frequency on each physical pair.
This isolates the repair and is a greedy search, not a global frequency optimum.
"""
import math
from collections import defaultdict


def pair(a, b):
    return tuple(sorted((a, b)))


def templates(nm, D, A, scen, nodes_all):
    """Original eligibility and standalone fixed-point frequencies, unchanged."""
    W = A['weeks_per_year']
    bases = ['MOW', 'SVX']
    open_nodes = [x for x in nodes_all if x not in nm.CLOSED and x not in bases]
    result = []
    for i, X in enumerate(open_nodes):
        for Y in open_nodes[i + 1:]:
            dxy = D.km(X, Y)
            if dxy < A['transfer_min_km'] or D.has_direct(X, Y) or dxy > D.green(X, Y):
                continue
            for B in bases:
                d1, d2 = D.km(B, X), D.km(Y, B)
                if d1 > D.green(B, X) or d2 > D.green(Y, B):
                    continue
                if d1 + d2 > A['triangle_detour_factor'] * dxy + A['triangle_detour_add_km']:
                    continue
                legs = [dict(a=a, b=b, km=km, south=D.south(a,b),
                             competitive=D.has_direct(a,b), dem=D.get(a,b,scen)/(2*W))
                        for a,b,km in ((B,X,d1),(X,Y,dxy),(Y,B,d2))]
                f = int(A['min_freq_week'])
                for _ in range(100):
                    pax = [L['dem'] * nm.leg_share(L,f,A) for L in legs]
                    nf = int(min(A['direct_max_freq_week'], max(A['min_freq_week'],
                             math.ceil(max(pax)/(A['seats']*A['lf_max'])))))
                    if nf == f:
                        break
                    f = nf
                result.append(dict(B=B, X=X, Y=Y, legs=legs, freq=f))
    return result


def weighted_capped(total, weights, caps):
    """Allocate a single pool, retaining spill as unsold. No duplicate claims."""
    target = min(max(0., total), sum(caps))
    out = [0.] * len(caps)
    active = {i for i,c in enumerate(caps) if c > 0}
    remaining = target
    while active and remaining > 1e-10:
        denom = sum(weights[i] for i in active)
        assert denom > 0
        shares = {i:remaining*weights[i]/denom for i in active}
        saturated = {i for i in active if shares[i] >= caps[i]-out[i]-1e-12}
        if not saturated:
            for i in active:
                out[i] += shares[i]
            remaining = 0.
            break
        for i in saturated:
            add = caps[i]-out[i]
            out[i] += add
            remaining -= add
        active -= saturated
    assert abs(sum(out)-target) < 1e-7
    return out


def evaluate(nm, selected, A, allocation='frequency', capture_law='author_at_total_frequency'):
    """One pool per unordered physical pair within a single alternative network.

    Two defensible scenario allocations: proportional to frequency, or to each
    program's original standalone claim. Both respect each program's capacity.
    The sum and pair fare are allocation invariant for fixed frequencies.
    """
    assert allocation in ('frequency','standalone_claim')
    assert capture_law in ('author_at_total_frequency','market_bound_only')
    groups = defaultdict(list)
    for ti,t in enumerate(selected):
        for li,L in enumerate(t['legs']):
            groups[pair(L['a'],L['b'])].append((ti,li,L,t['freq']))
    carried, markets = {}, []
    for key, occurrences in groups.items():
        L = occurrences[0][2]
        assert all(math.isclose(L['dem'],r[2]['dem'],rel_tol=1e-12)
                   and L['competitive']==r[2]['competitive']
                   and math.isclose(L['km'],r[2]['km'],rel_tol=1e-12) for r in occurrences)
        F = sum(r[3] for r in occurrences)
        caps = [r[3]*A['seats']*A['lf_max'] for r in occurrences]
        claims = [r[2]['dem']*nm.leg_share(r[2],r[3],A) for r in occurrences]
        physical_caps = list(caps)
        if capture_law=='market_bound_only':
            # Mandatory D/seat budget, without prescribing pooled Q(F). Preserve
            # each author's claim and its own seat cap, then enforce one D cap.
            pool = min(L['dem'],sum(claims))
            caps = [min(c,p) for c,p in zip(caps,claims)]
        else:
            # AGENT_PROPOSAL: author curve at combined frequency, not an
            # empirically established law and not implied uniquely by D cap.
            pool = min(L['dem'],L['dem'] * nm.leg_share(L,F,A))
        weights = [r[3] for r in occurrences] if allocation=='frequency' else claims
        amounts = weighted_capped(pool,weights,caps) if pool > 0 else [0.]*len(caps)
        for r,p in zip(occurrences,amounts):
            carried[r[0],r[1]] = p
        markets.append(dict(pair='-'.join(key),scenario_weekly_one_direction_market=L['dem'],
                            frequency_each_direction=F,captured_pool=pool,capacity_at_lf_max=sum(physical_caps),
                            sold=sum(amounts),spill=pool-sum(amounts),standalone_claim_sum=sum(claims),
                            competitive=L['competitive'],allocation=allocation,capture_law=capture_law))
    chosen = []
    for ti,t in enumerate(selected):
        h=c=r=s=0.
        out=[]
        for li,L in enumerate(t['legs']):
            p = carried[ti,li]
            f = t['freq']
            bh,lc = nm.leg_cost(A,L['km'],L['south'],p/f)
            h+=2*f*bh; c+=2*f*lc; r+=2*p*nm.fare(A,L['km']); s+=2*p
            out.append(dict(L,freq=f,carried_dir_week=p,block_h=bh,lf=p/(f*A['seats'])))
        chosen.append(((r-c)/h,t['B'],t['X'],t['Y'],h,c,r,s,out))
    return chosen,markets


def totals(chosen):
    return tuple(sum(c[k] for c in chosen) for k in (4,5,6,7))


def select(nm,D,A,scen,nodes_all,allocation='frequency',capture_law='author_at_total_frequency'):
    """Greedy marginal contribution/block-hour; all prior programs revalued."""
    candidates = templates(nm,D,A,scen,nodes_all)
    selected=[]; used=set(); current=[]
    max_h=(A['fleet_cap']-A['spare_aircraft'])*A['block_h_per_day']*7
    while len(selected) < A['max_routes']:
        old_h,old_c,old_r,_=totals(current)
        best=None
        for t in candidates:
            if pair(t['X'],t['Y']) in used:
                continue
            h=2*t['freq']*sum(nm.leg_cost(A,L['km'],L['south'],0)[0] for L in t['legs'])
            if old_h+h > max_h+1e-9:
                continue
            net,_=evaluate(nm,selected+[t],A,allocation,capture_law)
            nh,nc,nr,_=totals(net)
            score=((nr-nc)-(old_r-old_c))/(nh-old_h)
            if best is None or score > best[0]:
                best=(score,t,net)
        if best is None or (best[0] <= 0 and len(selected) >= A['min_routes']):
            break
        selected.append(best[1]); used.add(pair(best[1]['X'],best[1]['Y']))
        current=best[2]
    return current


def from_author(chosen):
    return [dict(B=c[1],X=c[2],Y=c[3],freq=c[8][0]['freq'],
                 legs=[{k:L[k] for k in ('a','b','km','south','competitive','dem')} for L in c[8]])
            for c in chosen]
