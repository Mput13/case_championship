#!/usr/bin/env python3
"""MR12 independent audit. All subject reads are exact git-show; writes stay here.

No owner module is imported by the independent reconstruction. Owner replay and
the refusal probe run subsequently in a disposable directory inside this scope.
"""
import collections
import csv
import hashlib
import io
import itertools
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
import scipy
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SUBJECT = 'ba9f6b85b4f8c9847948ae428ef3fbcfca9e2009'
PREPARED = 'c43e58569f3fc561bb7d0dd0806995b718ef01a9'
V5 = 'f7a034dc91917cc69c5f8b3a729c3d1c6dfeb5b9'
METHODS = 'context/23_night_run_20261110/methods/'
SRC = 'inputs/set001/tsiri_93fa/context/'
SOURCE = '93fa5cf4a10ab67e05c93d19fc5375fc58ef9299'
SEEN = {}
MAX_ERRORS = collections.defaultdict(float)
PAX_TOL = 2e-6
MONEY_TOL = 1e-4


def exact(path, ref=SUBJECT, methods=True, grain=None):
    path = METHODS + path if methods else path
    b = subprocess.check_output(['git', 'show', f'{ref}:{path}'], cwd=REPO)
    SEEN[ref + ':' + path] = dict(commit=ref, path=path, bytes=len(b),
        sha256=hashlib.sha256(b).hexdigest(), access='git show exact commit:path',
        grain=grain or ('table rows at the source file grain' if path.endswith('.csv') else 'code, contract or metadata'))
    return b


def rows(path):
    return list(csv.DictReader(io.StringIO(exact(path).decode('utf-8-sig'))))


def js(path):
    return json.loads(exact(path))


def save(name, value):
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    if name.endswith('.json'):
        p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    else:
        with p.open('w', newline='') as f:
            w = csv.DictWriter(f, list(dict.fromkeys(k for r in value for k in r)))
            w.writeheader()
            w.writerows(value)


def near(a, b, label, tol=MONEY_TOL):
    e = abs(float(a) - float(b))
    MAX_ERRORS[label] = max(MAX_ERRORS[label], e)
    assert e <= tol, (label, a, b, e, tol)


def unique(rs, key):
    d = {key(r): r for r in rs}
    assert len(d) == len(rs), ('duplicate full key', len(d), len(rs))
    return d


def pair(a, b):
    return tuple(sorted((a, b)))


def flight_cost(minutes, p):
    hours = minutes / 60
    return ((hours * p['fuel_t_per_hour'] + p['fuel_t_per_cycle']) *
            (p['fuel_rub_per_t'] + p['fuel_uplift_rub_per_t']) +
            hours * (p['mro_rub_per_hour'] + p['crew_rub_per_hour'] + p['navigation_rub_per_hour']) +
            (49.45 * (553 + 499) + 19300 + 8100 + 16668) * p['airport_factor'] +
            p['deicing_probability'] * p['deicing_operation_rub'])


def check_certificate(A, b, u, c, x, y, mu, label):
    """max c'x, Ax<=b, 0<=x<=u; min b'y+u'mu, A'y+mu>=c."""
    slack = b - A @ x
    reduced = A.T @ y + mu - c
    primal = float(c @ x)
    dual = float(b @ y + u @ mu)
    assert min(x) >= -PAX_TOL and min(u-x) >= -PAX_TOL, label
    assert min(slack) >= -PAX_TOL, (label, 'primal row', min(slack))
    assert min(y) >= -1e-7 and min(mu) >= -1e-7, label
    assert min(reduced) >= -1e-6, (label, 'dual row', min(reduced))
    near(primal, dual, 'duality_' + label.split('|')[-1])
    # Complementarity is checked in aggregate; no cancellation is allowed.
    comp = float(np.abs(y*slack).sum() + np.abs(mu*(u-x)).sum() + np.abs(reduced*x).sum())
    assert comp <= 5e-4, (label, 'complementarity', comp)
    return dict(primal=primal, dual=dual, gap=dual-primal,
                max_row_violation=max(0., float(-min(slack))),
                min_row_shadow=float(min(y)), min_upper_shadow=float(min(mu)),
                min_dual_slack=float(min(reduced)), complementarity_abs_sum=comp,
                upper_bound_term=float(u @ mu), constraint_term=float(b @ y))


def main():
    exact('context/23_night_run_20261110/contract.md', PREPARED, False)
    exact('context/23_night_run_20261110/briefs/allocation_variants_review.md', PREPARED, False)
    for f in ['decision_conditions.md', 'allocation_contract.json', 'final_variant_contract.json',
              'requests.json', 'allocation_diagnostic.py', 'common_demand.py', 'final_variant_synthesis.py',
              'budget_contract.json', 'update_acceptance_v6.py', 'render_allocation_chart.py', 'source_manifest.json']:
        exact(f)
    originals = rows(SRC+'21_team_proposals/comparison.csv')
    source_sales = rows(SRC+'17_aircraft_route_review/model/sales.csv')
    source_caps = rows(SRC+'17_aircraft_route_review/model/capacity.csv')
    source_flights = rows(SRC+'17_aircraft_route_review/model/flights.csv')
    config = js(SRC+'15_team_update/model/configuration.json')
    params = config['scenarios']
    legacy = js(SRC+'16_conditional_decision/assumptions.json')
    # Inspect the inherited definitions; do not execute source author code.
    for f in ['scripts/build_aircraft_route_review.py', 'scripts/build_team_comparison.py',
              'scripts/build_conditional_decision.py']:
        exact('inputs/set001/tsiri_93fa/'+f)
    # Verify frozen numeric/calendar source bytes against their originating commit.
    origin_checks = []
    for rel in ['21_team_proposals/comparison.csv', '17_aircraft_route_review/model/sales.csv',
                '17_aircraft_route_review/model/capacity.csv', '17_aircraft_route_review/model/flights.csv',
                '15_team_update/model/configuration.json', '16_conditional_decision/assumptions.json']:
        a = exact(SRC+rel)
        b = exact('context/'+rel, SOURCE, False)
        assert a == b, rel
        origin_checks.append(dict(path=rel, original_commit=SOURCE, sha256=hashlib.sha256(a).hexdigest(), equal=True))
    save('source_origin_checks.json', origin_checks)
    mapping = rows('runs/common_demand_v1/demand_mapping.csv')
    proxies = rows('inputs/set001/nastya_2f03/data/processed/demand_pairs.csv')
    proxy = unique(proxies, lambda r: pair(r['a'], r['b']))
    # N is reconstructed from the annual source, not just its published weekly mapping.
    for r in mapping:
        q = proxy[tuple(r['pair'].split('-'))]
        field = 'observed' if r['scenario']=='base' and q['observed'] and q['observed_coverage']!='airline_group' else 'pax_'+r['scenario']
        assert r['N_field'] == field
        near(r['N_week_direction_stress'], float(q[field])/104, 'N_annual_div104', PAX_TOL)
    nd = unique(mapping, lambda r:(r['network'], r['scenario'], tuple(r['pair'].split('-'))))
    summaries = unique(rows('runs/allocation_v1/summary.csv'), lambda r:(r['case_id'], r['objective']))
    allocations = rows('runs/allocation_v1/allocations.csv')
    duals = rows('runs/allocation_v1/constraint_duals.csv')
    certs = rows('runs/allocation_v1/offer_dual_certificates.csv')
    gates = unique(rows('runs/allocation_v1/migration_linearity_gates.csv'), lambda r:(r['case_id'],r['origin'],r['destination']))
    references = unique(rows('runs/allocation_v1/local_first_reference.csv'), lambda r:r['case_id'])
    bounds = unique(rows('runs/budget_v1/supply_upper_bounds.csv'), lambda r:(r['network'],r['scenario']))
    bound_certs = rows('runs/budget_v1/supply_dual_certificates.csv')
    cases = []
    for r in originals:
        cases.append((r, 'C', 1.))
        if r['network']!='D_previous_best8': cases.append((r, 'N', 1.))
        if r['network'] in ['H_UFA_4','H_UFA_8'] and r['scenario']=='base': cases.append((r, 'C', 3.))
    assert len(cases) == 16
    all_offers=[]; matrix=[]; primal_checks=[]; secondary_checks=[]; secondary_constraints=[]; secondary_offers=[]
    oracle_primary_constraints=[];oracle_primary_offers=[]
    gate_checks=[]; local_checks=[]; result_rows=[]; supply_checks=[]; cases_meta=[]
    for r,recipe,scale in cases:
        name,sc = r['network'],r['scenario']
        case = f'{name}|{sc}|{recipe}|{scale}'
        p = params[sc]
        source_key = (r['source_profile'],r['source_network'],sc)
        ss = [s for s in source_sales if (s['profile'],s['network'],s['scenario'])==source_key]
        cc = [s for s in source_caps if (s['profile'],s['network'],s['scenario'])==source_key]
        ff = [s for s in source_flights if (s['profile'],s['network'])==source_key[:2]]
        fm = unique(ff, lambda s:s['id'])
        cm = unique(cc, lambda s:s['flight_id'])
        assert set(fm) == set(cm) == {l for s in ss for l in s['flight_ids'].split(';')}
        assert int(r['active_allocated'])==len({f['aircraft'] for f in ff})
        freq = collections.Counter((s['origin'],s['destination']) for s in ss)
        known_pairs = {pair(s['origin'],s['destination']) for s in ss if s['known_direct_RW_capacity'] and float(s['known_direct_RW_capacity'])>0}
        offers=[]
        for s in ss:
            k=(s['origin'],s['destination']);legs=s['flight_ids'].split(';');trans=s['transfer']=='True'
            assert len(set(legs))==len(legs) and len(legs)==(2 if trans else 1)
            assert fm[legs[0]]['origin']==k[0] and fm[legs[-1]]['destination']==k[1]
            if trans: assert fm[legs[0]]['destination']==fm[legs[1]]['origin']
            assert all(fm[l]['day']==s['day'] for l in legs)
            D = float(s['D']) if recipe=='C' else float(proxy[pair(*k)]['observed' if sc=='base' and proxy[pair(*k)]['observed'] and proxy[pair(*k)]['observed_coverage']!='airline_group' else 'pax_'+sc])/104
            D *= scale
            capfrac=legacy['local_peak'][sc] * -math.expm1(-freq[k]/p['frequency_scale']) * (.65 if trans else 1)
            can=legacy['known_incumbent_migration'][sc] if pair(*k) in known_pairs else (.05 if sc=='base' else .1)
            known=float(s['known_direct_RW_capacity']) if s['known_direct_RW_capacity'] else None
            if float(s['sold_journeys'])>0:
                near(float(s['migrated_RW_total'])/float(s['sold_journeys']),can,'source_migration_share',1e-10)
            fare=float(s['fare_once']);oldfare=fare/(p['transfer_fare_factor'] if trans else 1)*p['old_RW_fare_ratio']
            offers.append(dict(key=(k[0],k[1],s['flight_ids']),k=k,legs=legs,transfer=trans,day=int(s['day']),
                               D=D,desired=D*capfrac/freq[k],can=can,known=known,fare=fare,oldfare=oldfare,source=s))
        # Owner certificate has only an integer offer index; reconstruct its exact order
        # once, then use stable full source itinerary keys for the independent LP.
        ordered = sorted(offers,key=lambda o:(o['transfer'],-(o['fare']-o['can']*o['oldfare']-len(o['legs'])*p['pax_cost'])/len(o['legs']),*o['k'],o['day'],tuple(o['legs'])))
        for idx,o in enumerate(ordered):o['owner_index']=idx
        offers.sort(key=lambda o:o['key'])
        assert len({o['key'] for o in offers})==len(offers)
        markets = collections.defaultdict(list)
        for i,o in enumerate(offers): markets[o['k']].append(i)
        leg_ids=sorted(cm);labels=['LEG|'+l for l in leg_ids];rhs=[float(cm[l]['capacity_scenario']) for l in leg_ids]
        arrays=[[int(l in o['legs']) for o in offers] for l in leg_ids]
        for k,indices in sorted(markets.items()):
            ds={offers[i]['D'] for i in indices};ks={offers[i]['known'] for i in indices};cs={offers[i]['can'] for i in indices}
            assert len(ds)==len(ks)==len(cs)==1
            D=ds.pop();known=ks.pop();can=cs.pop()
            possible=sum(min(offers[i]['desired'],*(float(cm[l]['capacity_scenario']) for l in offers[i]['legs'])) for i in indices)
            assert known is None or known==0 or can*possible<=known+1e-7
            g=gates[(case,*k)]
            near(g['optimistic_possible_sales'],possible,'global_gate_upper',PAX_TOL)
            near(g['can_times_sales_upper'],can*possible,'global_gate_migration',PAX_TOL)
            assert (g['known_own_cap']=='')==(known is None)
            if known is not None: near(g['known_own_cap'],known,'known_cap',PAX_TOL)
            near(g['can'],can,'gate_can',1e-10)
            oldsegments=1 if known is not None and known>0 else 2
            assert int(g['old_segments_per_migrated'])==oldsegments
            gate_checks.append(dict(case_id=case,origin=k[0],destination=k[1],market_D=D,known_own_cap=known,
                 source_migration_share=can,upper_sales_entire_polytope=possible,upper_migrated=can*possible,
                 direct_status='KNOWN_DIRECT_NONBINDING' if oldsegments==1 else ('UNKNOWN_UNVERIFIED_MIGRATION' if known is None else 'KNOWN_ZERO_DIRECT_UNVERIFIED_MIGRATION'),
                 old_segments_saved=oldsegments,proof='x_i<=min(u_i,each leg cap); sum then multiply by can',gate_pass=True))
            for i in indices:offers[i]['old_segments']=oldsegments
            arrays.append([int(i in indices) for i in range(len(offers))]);rhs.append(D);labels.append('OD|'+'-'.join(k))
        A=np.array(arrays,dtype=float);b=np.array(rhs);u=np.array([o['desired'] for o in offers]);w=np.array([o['fare']-o['can']*o['oldfare']-len(o['legs'])*p['pax_cost']+o['can']*o['old_segments']*p['pax_cost'] for o in offers])
        for l in leg_ids:
            c=cm[l];f=fm[l]
            assert (c['origin'],c['destination'])==(f['origin'],f['destination'])
            assert '2026-12-07'<=f['date']<='2026-12-13'
            near(c['block_minutes'],f['block_minutes'],'source_block_minutes',1e-9)
            near(c['flight_variable_cost'],flight_cost(float(f['block_minutes']),p),'source_flight_cost')
            assert float(c['capacity_scenario'])==float(f[sc+'_capacity_scenario'])
        cost=sum(flight_cost(float(f['block_minutes']),p) for f in ff)
        near(cost,r['flight_variable_cost'],'full_flight_cost')
        cases_meta.append(dict(case_id=case,candidate=name,scenario=sc,recipe=recipe,scale=scale,
            input_set_id='set001+fixed_offer_allocation_v1',source_commit=SOURCE,source_profile=source_key[0],source_network=source_key[1],
            period_start='2026-12-07',period_end='2026-12-13',currency='RUB',price_basis='CIRI_NET_SCENARIO_FARE',
            tax_basis='EX_RECOVERABLE_VAT_AS_AUTHOR_SCENARIO',offer_count=len(offers),leg_count=len(leg_ids),directed_pool_count=len(markets),flight_cost=cost))
        # Exact local-first mechanics, including the source migration ledger.
        remaining={l:float(cm[l]['capacity_scenario']) for l in leg_ids}
        migration={k:(offers[indices[0]]['known'] or 0) for k,indices in markets.items()}
        x0map={};ref_money=0.;ref_direct=0.;ref_unknown=0.
        for o in ordered:
            z=min(o['desired'],*(remaining[l] for l in o['legs']))
            for l in o['legs']:remaining[l]-=z
            direct=min(z*o['can'],migration[o['k']]);migration[o['k']]-=direct
            unknown=z*o['can']-direct
            ref_direct+=direct;ref_unknown+=unknown
            ref_money+=z*o['fare']-(direct+unknown)*o['oldfare']-z*len(o['legs'])*p['pax_cost']+(direct+2*unknown)*p['pax_cost']
            x0map[o['key']]=z
        x0=np.array([x0map[o['key']] for o in offers]);ref=ref_money-cost
        assert min(b-A@x0)>=-PAX_TOL and min(u-x0)>=-PAX_TOL and min(x0)>=0
        near(w@x0-cost,ref,'local_linear_accounting')
        reference=references[case]
        for k,v in [('local_first_contribution',ref),('local_first_journeys',sum(x0)),
                    ('local_first_segments',sum(len(o['legs'])*z for o,z in zip(offers,x0))),
                    ('local_first_transfers',sum(z for o,z in zip(offers,x0) if o['transfer']))]:
            near(reference[k],v,'local_reference_'+k)
        if recipe=='C' and scale==1:
            for o,z in zip(offers,x0):near(o['source']['sold_journeys'],z,'source_local_first_sold',PAX_TOL)
            near(r['contribution_before_base_fleet_opportunity'],ref,'original_comparison_local_first')
            near(r['migrated_RW_direct'],ref_direct,'source_known_direct',PAX_TOL)
            near(r['migrated_RW_unverified_connecting'],ref_unknown,'source_unverified_migration',PAX_TOL)
        local_checks.append(dict(case_id=case,contribution=ref,journeys=float(sum(x0)),
            known_direct_migrated=ref_direct,unverified_migrated=ref_unknown,min_OD_leg_slack=float(min(b-A@x0)),feasible=True))
        # Rebuild the MR07 relaxation only within its original enumerated universe.
        relaxed=np.array([o['fare']-len(o['legs'])*p['pax_cost'] for o in offers])
        legA=A[:len(leg_ids)];legb=b[:len(leg_ids)]
        sh=np.array([max([0.]+[relaxed[i] for i,o in enumerate(offers) if o['legs']==[l]]) for l in leg_ids])
        assert min(sh)>=0 and min(legA.T@sh-relaxed)>=-1e-6
        assert min(relaxed-w)>=-1e-6, 'zero-migration is optimistic in this product universe'
        upper=float(legb@sh-cost)
        near(bounds[name,sc]['optimistic_contribution_upper'],upper,'MR07_bound')
        bc=unique([z for z in bound_certs if(z['network'],z['scenario'])==(name,sc)],lambda z:(z['origin'],z['destination'],z['flight_ids']))
        assert set(bc)=={o['key'] for o in offers}
        for i,o in enumerate(offers):
            q=bc[o['key']];near(q['itinerary_unit_margin'],relaxed[i],'MR07_product_margin')
            near(q['sum_leg_shadow_value'],legA[:,i]@sh,'MR07_product_shadow')
        supply_checks.append(dict(case_id=case,product_universe='exact source profile/network/scenario offered itineraries only',
            margin_dominance_min=float(min(relaxed-w)),supply_upper=upper,certificate='nonnegative per-leg local margins dominate every listed product'))
        for i,o in enumerate(offers):
            all_offers.append(dict(case_id=case,source_profile=source_key[0],source_network=source_key[1],origin=o['k'][0],destination=o['k'][1],
                 flight_ids=o['key'][2],owner_offer_index=o['owner_index'],desired=o['desired'],market_D=o['D'],unit_fare=o['fare'],
                 migration_share=o['can'],old_fare=o['oldfare'],old_segments_saved=o['old_segments'],
                 new_segments=len(o['legs']),pax_cost=p['pax_cost'],contribution_coefficient=float(w[i]),local_first_sold=float(x0[i])))
            matrix.append(dict(case_id=case,offer=i,origin=o['k'][0],destination=o['k'][1],flight_ids=o['key'][2],
                 nonzero_constraints=';'.join(labels[j] for j in range(len(labels)) if A[j,i]),upper=float(u[i]),lower=0))
        for objective,v in [('CONTRIBUTION',w),('ENDPOINT_JOURNEYS',np.ones(len(offers))),('PASSENGER_SEGMENTS',np.array([len(o['legs']) for o in offers],dtype=float))]:
            key=case,objective;s=summaries[key]
            ar=unique([z for z in allocations if(z['case_id'],z['objective'])==key],lambda z:(z['origin'],z['destination'],z['flight_ids']))
            assert set(ar)=={o['key'] for o in offers}
            x=np.array([float(ar[o['key']]['allocated']) for o in offers])
            dr=unique([z for z in duals if(z['case_id'],z['objective'])==key],lambda z:z['constraint'])
            cr=unique([z for z in certs if(z['case_id'],z['objective'])==key],lambda z:int(z['offer']))
            assert set(dr)==set(labels) and set(cr)==set(range(len(offers)))
            y=np.array([float(dr[l]['shadow']) for l in labels]);mu=np.array([float(cr[o['owner_index']]['offer_upper_shadow']) for o in offers])
            for j,l in enumerate(labels):near(dr[l]['rhs'],b[j],'certificate_rhs',PAX_TOL)
            for i,o in enumerate(offers):
                q=cr[o['owner_index']]
                for field,value in [('objective_coefficient',v[i]),('sum_constraint_shadow',A[:,i]@y),
                                    ('dual_slack',A[:,i]@y+mu[i]-v[i]),('desired',u[i])]:near(q[field],value,'published_certificate_'+field)
            ck=check_certificate(A,b,u,v,x,y,mu,case+'|'+objective)
            for field,value in [('primary_optimum',v@x),('primary_dual_certificate',ck['dual']),('primary_achieved',v@x)]:near(s[field],value,'summary_'+field)
            sol=linprog(-v,A_ub=A,b_ub=b,bounds=list(zip(np.zeros(len(u)),u)),method='highs-ds')
            assert sol.success,sol.message
            near(-sol.fun,ck['dual'],'independent_primary_optimum')
            oy=-sol.ineqlin.marginals;om=-sol.upper.marginals
            ock=check_certificate(A,b,u,v,x,oy,om,case+'|ORACLE_PRIMARY')
            for l,rhs,shadow in zip(labels,b,oy):oracle_primary_constraints.append(dict(case_id=case,objective=objective,constraint=l,rhs=float(rhs),shadow=float(shadow)))
            for i,o in enumerate(offers):oracle_primary_offers.append(dict(case_id=case,objective=objective,origin=o['k'][0],destination=o['k'][1],flight_ids=o['key'][2],
                coefficient=float(v[i]),constraint_shadow=float(A[:,i]@oy),upper_shadow=float(om[i]),dual_slack=float(A[:,i]@oy+om[i]-v[i]),upper=float(u[i])))
            primal_checks.append(dict(case_id=case,objective=objective,**ck,oracle_primary=-sol.fun,oracle_dual=ock['dual'],oracle_gap=ock['gap'],status='PASS'))
            tie_opt=None
            if objective!='CONTRIBUTION':
                At=np.vstack([A,-v]);bt=np.append(b,-float(s['primary_optimum'])+1e-8)
                tie=linprog(-w,A_ub=At,b_ub=bt,bounds=list(zip(np.zeros(len(u)),u)),method='highs-ds')
                assert tie.success,tie.message
                ty=-tie.ineqlin.marginals;tm=-tie.upper.marginals
                tck=check_certificate(At,bt,u,w,x,ty,tm,case+'|SECONDARY')
                near(w@x,-tie.fun,'independent_secondary_optimum')
                near(s['secondary_profit_dual_before_flight_cost'],tck['dual'],'published_secondary_value')
                assert float(v@x)>=float(s['primary_optimum'])-PAX_TOL
                tie_opt=float(-tie.fun)
                secondary_checks.append(dict(case_id=case,objective=objective,**tck,
                    primary_optimum=float(s['primary_optimum']),primary_achieved=float(v@x),
                    new_row_rhs=float(bt[-1]),new_row_shadow=float(ty[-1]),preserved_primary=True,status='PASS'))
                for l,rhs,shadow in zip(labels+['PRIMARY_OPTIMUM_LOWER_BOUND'],bt,ty):secondary_constraints.append(dict(case_id=case,objective=objective,constraint=l,rhs=float(rhs),shadow=float(shadow)))
                for i,o in enumerate(offers):secondary_offers.append(dict(case_id=case,objective=objective,origin=o['k'][0],destination=o['k'][1],flight_ids=o['key'][2],
                    coefficient=float(w[i]),constraint_shadow=float(At[:,i]@ty),upper_shadow=float(tm[i]),dual_slack=float(At[:,i]@ty+tm[i]-w[i]),upper=float(u[i])))
            tot=collections.Counter()
            known_direct=0.;unverified=0.
            for i,(o,z) in enumerate(zip(offers,x)):
                direct=z*o['can'] if o['old_segments']==1 else 0.
                unknown=z*o['can']-direct;known_direct+=direct;unverified+=unknown
                values=dict(journeys=z,segments=z*len(o['legs']),transfers=z if o['transfer'] else 0.,own_migrated_journeys=z*o['can'],
                    net_new_RW_journeys=z*(1-o['can']),gross=z*o['fare'],foregone=z*o['can']*o['oldfare'],
                    new_pax=z*len(o['legs'])*p['pax_cost'],saved_old_pax=(direct+2*unknown)*p['pax_cost'])
                tot.update(values)
                for field,value in values.items():near(ar[o['key']][field],value,'allocation_'+field)
                for field,value in [('desired',u[i]),('local_first_sold',x0[i]),('unit_incremental_margin',w[i])]:near(ar[o['key']][field],value,'allocation_'+field)
            C=tot['gross']-tot['foregone']-tot['new_pax']+tot['saved_old_pax']-cost
            near(C,w@x-cost,'contribution_accounting')
            for field in ['journeys','segments','transfers','own_migrated_journeys','net_new_RW_journeys']:near(s[field],tot[field],'summary_'+field)
            near(s['contribution'],C,'summary_contribution');near(s['local_first_contribution'],ref,'summary_local_reference')
            near(s['contribution_delta_vs_local_first'],C-ref,'summary_gain');near(s['supply_upper_bound'],upper,'summary_bound')
            near(tot['segments'],tot['journeys']+tot['transfers'],'unit_journey_segments',PAX_TOL)
            near(tot['journeys'],tot['own_migrated_journeys']+tot['net_new_RW_journeys'],'unit_own_net_new',PAX_TOL)
            assert C<=upper+MONEY_TOL and v@x>=v@x0-PAX_TOL
            if objective=='CONTRIBUTION': assert C>=ref-MONEY_TOL
            assert s['candidate']==name and s['scenario']==sc and s['recipe']==recipe and float(s['scale'])==scale
            assert s['full_budget']=='' and s['independent_review']=='PENDING' and int(s['active_allocated'])==int(r['active_allocated'])
            result_rows.append(dict(case_id=case,objective=objective,contribution=C,journeys=tot['journeys'],segments=tot['segments'],transfers=tot['transfers'],
                own_migrated=tot['own_migrated_journeys'],known_direct_migrated=known_direct,unverified_migrated=unverified,net_new_RW=tot['net_new_RW_journeys'],
                gross=tot['gross'],foregone=tot['foregone'],new_pax=tot['new_pax'],saved_old_pax=tot['saved_old_pax'],
                fixed_flight_cost=cost,local_first=ref,gain_vs_local=C-ref,secondary_optimum_before_flight=tie_opt))
    assert len(primal_checks)==48 and len(secondary_checks)==32 and len(gate_checks)==376
    for fn,data in [('case_register.csv',cases_meta),('coefficients.csv',all_offers),('constraint_matrix_sparse.csv',matrix),
                    ('primary_checks.csv',primal_checks),('secondary_checks.csv',secondary_checks),('secondary_constraint_duals.csv',secondary_constraints),
                    ('secondary_offer_certificates.csv',secondary_offers),('migration_gate_checks.csv',gate_checks),('local_first_checks.csv',local_checks),
                    ('oracle_primary_constraint_duals.csv',oracle_primary_constraints),('oracle_primary_offer_certificates.csv',oracle_primary_offers),
                    ('allocation_results.csv',result_rows),('supply_bound_checks.csv',supply_checks)]:save(fn,data)
    lookup={(r['case_id'],r['objective']):r for r in result_rows}
    base=lookup['H_UFA_8|base|C|1.0','CONTRIBUTION'];seg=lookup['H_UFA_8|base|C|1.0','PASSENGER_SEGMENTS']
    near(seg['segments']-base['segments'],56.304,'key_segments_rounded',.0006)
    near(seg['contribution']-base['contribution'],-90087.03,'key_money_rounded',.0051)
    near(seg['journeys'],base['journeys'],'key_same_journeys',PAX_TOL)
    near(lookup['H_UFA_4|base|C|1.0','CONTRIBUTION']['gain_vs_local'],42361.75,'Cbase_UFA4_rounded',.0051)
    near(base['gain_vs_local'],71612.45,'Cbase_UFA8_rounded',.0051)
    assert all(r['contribution']<0 for r in result_rows if not r['case_id'].endswith('|3.0'))
    save('key_counterexample.json',dict(contribution_optimum=base,segments_optimum=seg,
        delta_segments=seg['segments']-base['segments'],delta_money=seg['contribution']-base['contribution'],delta_journeys=seg['journeys']-base['journeys'],
        decision_status='OPEN_DECISION; scenario allocation objectives are not measured demand or a team choice'))
    check_variants(originals,source_flights)
    check_preservation()
    owner_replay_and_gate_probe()
    save('independent_checks.json',dict(status='PASS_SCOPED',subject=SUBJECT,prepared_root=PREPARED,
         cases=16,primary=48,secondary=32,migration_markets=376,finite_unions=15,pair_members=204,budget_conditions=90,joint_necessary_model_gates_pass=5,
         numerical_tolerance=dict(pax_absolute=PAX_TOL,money_absolute_RUB=MONEY_TOL,complementarity_abs_sum=5e-4,
             rationale='1e-8 primary tie relaxation can consume up to about 1e-4 RUB via finite coefficients; tolerances are far below 0.01 RUB reported money and 0.001 scenario pax'),
         python=sys.version,scipy=scipy.__version__,numpy=np.__version__,independent_solver='scipy.optimize.linprog highs-ds, own matrix/order/accounting',
         distinct_solver_implementation=False,max_errors=dict(MAX_ERRORS),source_live_reads=False,owner_code_used_as_only_oracle=False,
         outside_scope=['observed OD or net fares','actual aircraft/crew/base/dispatch','integer bookings','network/pricing optimization','MR11 cancellation audit','frontier review','full PnL/peak cash/launch','team objective selection']))
    save('source_manifest.json',dict(subject=SUBJECT,prepared_root=PREPARED,entries=list(SEEN.values()),
         live_folders_read=False,source_files_modified=False,hash_semantics='exact Git blob bytes only; not source empirical truth'))
    print(json.dumps(dict(status='PASS_SCOPED',cases=16,primary=48,secondary=32,unions=15,budgets=90)))


def check_variants(originals, flights):
    published=unique(rows('runs/final_variants_v1/network_union.csv'),lambda r:r['portfolio'])
    published_members=unique(rows('runs/final_variants_v1/network_pair_members.csv'),lambda r:(r['portfolio'],r['airport_a'],r['airport_b']))
    budgets=unique(rows('runs/final_variants_v1/budget_conditions.csv'),lambda r:(r['portfolio'],r['scenario'],r['capture_law']))
    portfolios=unique(rows('runs/portfolio_v2/summary.csv'),lambda r:(r['portfolio'],r['scenario'],r['capture_law']))
    assert len(budgets)==len(portfolios)==90 and set(budgets)==set(portfolios)
    source={}
    for r in originals:
        if r['scenario']!='base':continue
        ff=[f for f in flights if(f['profile'],f['network'])==(r['source_profile'],r['source_network'])]
        assert len({f['id'] for f in ff})==len(ff)
        working=len({f['aircraft'] for f in ff})
        assert working==int(r['active_allocated'])
        source[r['network']]=dict(row=r,flights=ff,working=working,pairs={pair(f['origin'],f['destination']) for f in ff})
    result=[];members=[];leg_rows=[];bcheck=[]
    for size in range(1,5):
        for subset in itertools.combinations(sorted(source),size):
            name='+'.join(subset);rr=published[name]
            working=sum(source[n]['working'] for n in subset)
            pairs={pair(f['origin'],f['destination']) for n in subset for f in source[n]['flights']}
            assert not any('MOW' in k for k in pairs)
            dated=sum(len(source[n]['flights']) for n in subset)
            base=int(any(n.startswith('H_UFA_') for n in subset))
            both=8<=len(pairs)<=12 and working<=4
            sum_pairs=sum(len(source[n]['pairs']) for n in subset)
            for field,value in [('component_count',size),('sum_component_pair_counts',sum_pairs),('unique_model_airport_pairs',len(pairs)),
                                ('duplicate_pair_count_removed',sum_pairs-len(pairs)),('model_dated_flight_instances',dated),
                                ('working_allocated',working),('reserve_assumption',1),('new_UFA_base_count',base)]:
                assert int(rr[field])==value,(name,field)
            assert rr['airport_pairs']==';'.join('-'.join(k) for k in sorted(pairs))
            assert rr['model_8_12_count_gate']==str(8<=len(pairs)<=12)
            assert rr['current4_working_gate']==str(working<=4) and rr['joint_model_gates_pass']==str(both)
            assert rr['accepted_operating_routes']==rr['actual_available_aircraft']=='' and rr['complete_case_acceptance']=='False'
            assert rr['input_set_id']=='FINAL_VARIANT_SYNTHESIS_V1'
            result.append(dict(portfolio=name,components=size,airport_pairs=len(pairs),sum_component_pairs=sum_pairs,removed_duplicates=sum_pairs-len(pairs),
                dated_flights=dated,working_allocated_labels=working,pooled_reserve_assumption=1,one_UFA_base_assumption=base,
                joint_necessary_model_gates_pass=both,operating_acceptance=False))
            for k in sorted(pairs):
                producers=[n for n in subset if k in source[n]['pairs']]
                ff=[(n,f) for n in producers for f in source[n]['flights'] if pair(f['origin'],f['destination'])==k]
                q=published_members[name,*k]
                ids=';'.join(n+'|'+f['id'] for n,f in ff)
                keys=';'.join(n+'|'+source[n]['row']['source_profile']+'|'+source[n]['row']['source_network'] for n in producers)
                assert q['namespaced_flight_ids']==ids and q['component_programs']==';'.join(producers) and q['source_keys']==keys
                assert int(q['dated_flight_instances'])==len(ff)
                assert q['date_min']==min(f['date'] for n,f in ff) and q['date_max']==max(f['date'] for n,f in ff)
                assert q['operating_acceptance']=='NOT_ESTABLISHED'
                members.append(dict(portfolio=name,airport_a=k[0],airport_b=k[1],source_keys=keys,namespaced_flight_ids=ids,
                                    dated_flights=len(ff),date_min=q['date_min'],date_max=q['date_max'],status='PASS'))
                for n,f in ff:leg_rows.append(dict(portfolio=name,airport_a=k[0],airport_b=k[1],component=n,source_profile=f['profile'],
                    source_network=f['network'],flight_id=f['id'],date=f['date'],day=f['day'],origin=f['origin'],destination=f['destination'],
                    aircraft_label=f['aircraft'],departure_utc_minute=f['departure_utc_minute'],arrival_utc_minute=f['arrival_utc_minute']))
            for sc in ['base','cautious']:
                for law in ['D_GUARD_STANDALONE_CLAIMS','COUNT_ALL_OFFERS','COUNT_DISTINCT_DEPARTURE_TIMES']:
                    key=(name,sc,law);q=budgets[key];p=portfolios[key]
                    C=float(p['contribution_before_base_fleet_opportunity'])
                    source_identity=(float(p['gross_revenue'])-float(p['foregone_RW_revenue'])-
                                     float(p['flight_variable_cost'])-float(p['new_pax_variable'])+float(p['saved_old_pax_variable']))
                    near(C,source_identity,'portfolio_source_money_identity')
                    near(q['contribution_before_base_fleet_opportunity'],C,'budget_exact_source_C',1e-9)
                    assert int(p['working_required'])==working and int(p['new_UFA_base_count'])==base
                    assert q['money_input_set_id']==p['input_set_id']=='CONTEXT21_PORTFOLIO_D_GUARD_V2'
                    assert q['money_period']==p['numerical_price_period']=='CIRI_NET_RUB_WEEK_20261207_13'
                    assert q['union_input_set_id']=='FINAL_VARIANT_SYNTHESIS_V1'
                    assert q['full_PnL']==q['peak_cash_need']==p['full_budget']==''
                    assert int(q['model_airport_pairs'])==len(pairs) and int(q['working_allocated'])==working
                    assert q['joint_model_gates_pass']==str(both)
                    assert int(q['n_if_every_working_and_one_reserve_are_incremental'])==working+1
                    assert int(q['b_if_new_UFA_base_is_incremental'])==base
                    near(q['required_external_donor_gain_if_excluded_costs_zero'],-C,'budget_donor_intercept',1e-9)
                    assert q['required_donor_gain_general']=='-C + F_incremental + B_incremental + S_excluded + L_recognized'
                    assert q['negative_if_external_donor_zero_and_excluded_costs_nonnegative']=='True' and C<0
                    assert q['decision_status']=='CONDITIONAL_COMPARISON_NO_WINNER'
                    # Two explicit nonnegative completion scenarios on each side of
                    # the donor boundary; these numbers are fixtures, not estimates.
                    for F,B,S,L in [(0.,0.,0.,0.),(125000.,25000.,5000.,1000.)]:
                        threshold=-C+F+B+S+L
                        for epsilon in [-1.,0.,1.]:
                            pnl=C+(threshold+epsilon)-F-B-S-L
                            near(pnl,epsilon,'budget_boundary_identity',1e-6)
                    bcheck.append(dict(portfolio=name,scenario=sc,capture_law=law,source_input_set_id=p['input_set_id'],
                        source_money_period=p['numerical_price_period'],source_C=C,donor_zero_nonnegative_excluded_is_negative=True,
                        donor_threshold_excluded_zero=-C,full_PnL=None,peak_cash=None,source_exact_value_preserved=True))
    assert len(result)==15 and len(members)==204 and len(published_members)==204 and len(bcheck)==90
    assert sum(r['joint_necessary_model_gates_pass'] for r in result)==5
    look={r['portfolio']:r for r in result}
    assert (look['D_SVX8+H_UFA_4']['airport_pairs'],look['D_SVX8+H_UFA_4']['working_allocated_labels'])==(12,3)
    assert (look['D_previous_best8+H_UFA_4']['airport_pairs'],look['D_previous_best8+H_UFA_4']['working_allocated_labels'])==(12,4)
    assert (look['H_UFA_4+H_UFA_8']['airport_pairs'],look['H_UFA_4+H_UFA_8']['working_allocated_labels'])==(8,6)
    save('independent_unions.csv',result);save('independent_pair_members.csv',members)
    save('independent_dated_legs.csv',leg_rows);save('independent_budget_conditions.csv',bcheck)
    save('budget_scope_probes.json',dict(
        identity='DeltaPnL = C + D_external - F_incremental - B_incremental - S_excluded - L_recognized',
        tests=[dict(name='do_not_double_subtract_migration',fixture_C=-100.,foregone_revenue_already_inside_C=30.,
                    named_external_donor_delta=0.,correct_delta=-100.,incorrect_duplicate_subtraction=-130.),
               dict(name='KEEP_unavoidable_fixed_is_not_incremental',fixed_KEEP=50.,fixed_action=50.,incremental_F=0.),
               dict(name='one_off_launch_is_not_perpetual_weekly',one_off=100.,recognition='requires explicit period/policy',weekly_forever=None),
               dict(name='refundable_deposit_is_separate_cash',deposit=200.,cash_outflow=200.,automatic_PnL_expense=0.),
               dict(name='KEEP_delta_zero_does_not_establish_company_profit',delta_vs_KEEP=0.,company_profit=None)],
        fixture_only=True,cash_fixtures_are_not_real_reserve=[1000000,1800000,6078000],
        donor_actual=None,resource_actual=None,future_delivery_dates=None,operating_network_accepted=False))


def check_preservation():
    listing=subprocess.check_output(['git','ls-tree','-r','--name-only',V5,METHODS],cwd=REPO,text=True).splitlines()
    selected=[p for p in listing if p.startswith(METHODS+'inputs/') or p.startswith(METHODS+'runs/') or p.startswith(METHODS+'analysis/')]
    counts=collections.Counter(p[len(METHODS):].split('/')[0] for p in selected)
    assert counts['inputs']+counts['runs']==320 and counts['analysis']==7 and len(selected)==327,counts
    checks=[]
    for p in selected:
        old=exact(p,V5,False);new=exact(p,SUBJECT,False)
        assert old==new,('frozen changed',p)
        checks.append(dict(path=p,old_commit=V5,new_commit=SUBJECT,sha256=hashlib.sha256(old).hexdigest(),bytes=len(old),byte_identical=True))
    save('v5_preservation_checks.csv',checks)
    save('preservation_summary.json',dict(status='PASS',inputs_and_runs=320,analysis=7,total=327,
        category_counts=dict(counts),old_commit=V5,subject=SUBJECT,personal_check=True,
        note='Git byte equality only; previous MR09/MR10/MR11/frontier verdicts are not re-reviewed or expanded'))


def owner_replay_and_gate_probe():
    # A supplementary deterministic replay. No owner module informs the independent
    # coefficients, matrix, primal checks or certificates written above.
    needed=['common_demand.py','allocation_diagnostic.py','final_variant_synthesis.py','update_acceptance_v6.py',
            'render_allocation_chart.py','allocation_contract.json','final_variant_contract.json',
            SRC+'21_team_proposals/comparison.csv',SRC+'17_aircraft_route_review/model/sales.csv',
            SRC+'17_aircraft_route_review/model/capacity.csv',SRC+'17_aircraft_route_review/model/flights.csv',
            SRC+'15_team_update/model/configuration.json','runs/common_demand_v1/demand_mapping.csv',
            'runs/budget_v1/supply_upper_bounds.csv','runs/portfolio_v2/summary.csv',
            'runs/admission_v1/acceptance_matrix.csv','runs/admission_v1/market_source_qualification.csv']
    checks=[];commands=[]
    with tempfile.TemporaryDirectory(prefix='owner_replay_',dir=ROOT) as d:
        base=Path(d)
        for p in needed:
            dest=base/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(exact(p))
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
        for command in ['allocation_diagnostic.py','final_variant_synthesis.py','update_acceptance_v6.py','render_allocation_chart.py']:
            run=subprocess.run([sys.executable,'-B',str(base/command)],env=env,cwd=base,text=True,capture_output=True,timeout=60)
            commands.append(dict(script=command,returncode=run.returncode,stdout=run.stdout,stderr=run.stderr))
            assert run.returncode==0,commands[-1]
        outputs=sorted(p for sub in ['runs/allocation_v1','runs/final_variants_v1','runs/admission_v2'] for p in (base/sub).iterdir() if p.is_file())
        assert len(outputs)==15,len(outputs)
        for p in outputs:
            rel=str(p.relative_to(base));a=p.read_bytes();b=exact(rel)
            assert a==b,('owner deterministic replay mismatch',rel)
            checks.append(dict(path=rel,bytes=len(a),sha256=hashlib.sha256(a).hexdigest(),byte_identical=True))
        # Force a real binding kink on an existing positive-known market by shrinking
        # all its source rows' old direct cap. This is an in-memory refusal probe.
        probe="""import allocation_diagnostic as a
orig=a.m.rows
def altered(path):
    rr=orig(path)
    if path.name=='sales.csv':
        for r in rr:
            if r['profile']=='UNKNOWN_TIME_PLUS60_100' and r['network']=='D_case' and r['scenario']=='base' and r['known_direct_RW_capacity'] and float(r['known_direct_RW_capacity'])>0:
                r['known_direct_RW_capacity']='0.001'
    return rr
a.m.rows=altered
a.main()
"""
        run=subprocess.run([sys.executable,'-B','-c',probe],env=env,cwd=base,text=True,capture_output=True,timeout=60)
        assert run.returncode!=0 and 'binding migration kink; LP held' in run.stderr,dict(returncode=run.returncode,stderr=run.stderr)
        # The mathematical counterexample has feasible x below and above K/can.
        save('migration_kink_counterexample.json',dict(
            synthetic=True,known_direct_cap=5.,can=.6,desired_upper=20.,leg_capacity=20.,directed_market_D=20.,
            required_linear_gate_upper=.6*20,gate_pass=False,kink_sales=5/.6,
            points=[dict(x=x,direct_migration=min(.6*x,5),unverified_migration=max(0,.6*x-5),
                         saved_old_segments=min(.6*x,5)+2*max(0,.6*x-5)) for x in [0.,5.,10.,20.]],
            reason='saved old segments slope changes from can to 2*can; one LP coefficient is invalid',
            owner_refusal_probe=dict(modification='in-memory positive-known source caps to0.001, D_SVX8/base; original Git bytes unchanged',
                returncode=run.returncode,stdout=run.stdout,stderr=run.stderr.replace(str(base),'<temporary_replay_scope>'),
                normalization='Only temporary directory path replaced; exception text and source line unchanged'),
            zero_unknown_cases=[dict(known_cap=0,known_direct_migrated=0,unverified=.6*20,saved_segments=2*.6*20),
                                dict(known_cap=None,known_direct_migrated=0,unverified=.6*20,saved_segments=2*.6*20)],
            zero_unknown_not_evidence_of_zero_actual_RW_migration=True))
    save('owner_replay_checks.json',dict(status='PASS_BYTE_IDENTICAL',new_outputs=15,files=checks,commands=commands,
        supplementary_only=True,independent_oracle_is_reconstruction_not_owner_replay=True,
        temporary_runtime_removed=True,new_dependencies=False,network_calls=False))


if __name__=='__main__':
    main()
