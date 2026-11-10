#!/usr/bin/env python3
"""MR13: pinned Git inputs, independent Fraction arithmetic; no owner imports."""
import collections
import csv
import hashlib
import io
import itertools
import json
import os
from pathlib import Path
from fractions import Fraction as Q
import shutil
import subprocess
import sys

SUBJECT = 'c6adf25cc39712cbfdd2d34acdabd31366b33bce'
BASE = 'ba9f6b85b4f8c9847948ae428ef3fbcfca9e2009'
ROOT_PIN = 'b20d4346b6aede514dbed59112bcf878232819c8'
P = 'context/23_night_run_20261110/methods/'
OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
DOMAINS = ['NO_FINAL_ROUTE_COUNT_GATE', 'FINAL_MODEL_PAIR_COUNT_8_12',
           'FINAL_MODEL_PAIR_COUNT_8_12_AND_NEW_UFA_BASE']
TOL = Q('0.00001')  # RUB, only serialized IEEE-754 owner arithmetic
CACHE = {}
READS = {}
CHECKS = []


def git(*args, cwd=REPO):
    return subprocess.check_output(['git', *args], cwd=cwd)


def blob(sha, path):
    key = sha, path
    if key not in CACHE:
        data = git('show', sha + ':' + path)
        CACHE[key] = data
        READS[key] = dict(source_commit=sha, path=path, bytes=len(data),
                          sha256=hashlib.sha256(data).hexdigest(),
                          grain='exact Git blob; CSV grain recorded in independent tables')
    return CACHE[key]


def table(name, sha=SUBJECT, full=False):
    return list(csv.DictReader(io.StringIO(blob(sha, name if full else P+name).decode('utf-8-sig'))))


def obj(name, sha=SUBJECT):
    return json.loads(blob(sha, P+name))


def text(name, sha=SUBJECT):
    return blob(sha, P+name).decode()


def save(name, value):
    path = OUT/name
    path.parent.mkdir(parents=True, exist_ok=True)
    if name.endswith('.json'):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    else:
        with path.open('w', newline='') as f:
            w = csv.DictWriter(f, list(dict.fromkeys(k for r in value for k in r)))
            w.writeheader()
            w.writerows(value)


def check(name, condition, detail=None):
    assert condition, (name, detail)
    CHECKS.append(dict(check=name, status='PASS', detail=detail))


def number(x):
    return float(x) if x is not None else None


def close(a, b):
    return abs(Q(str(a))-Q(str(b))) <= TOL


def score(a, f, b):
    return a['c']-a['n']*f-a['b']*b


def planes(a, others):
    return [(a['n']-v['n'], a['b']-v['b'], a['c']-v['c'])
            for v in others if a['name'] != v['name']] + [(-1, 0, Q(0)), (0, -1, Q(0))]


def vertices(hs):
    result = set()
    for (a,b,c),(d,e,f) in itertools.combinations(hs,2):
        determinant = a*e-b*d
        if not determinant:
            continue
        x,y = (c*e-b*f)/determinant, (a*f-c*d)/determinant
        if all(i*x+j*y <= k for i,j,k in hs):
            result.add((x,y))
    return sorted(result)


def tie_edge(a, b, others):
    """Exact interval on a pair equality, clipped by every alternative and axes."""
    af,bb,rhs = a['n']-b['n'], a['b']-b['b'], a['c']-b['c']
    if not af and not bb:
        return None
    if bb:
        x0,x1,y0,y1 = Q(0),Q(1),rhs/bb,Q(-af,bb)
        parameter='F'
    else:
        x0,x1,y0,y1 = rhs/af,Q(0),Q(0),Q(1)
        parameter='B'
    lower,upper = None,None
    for i,j,k in planes(a,others):
        coefficient = i*x1+j*y1
        bound = k-i*x0-j*y0
        if not coefficient:
            if bound < 0:
                return None
        elif coefficient > 0:
            upper = bound/coefficient if upper is None else min(upper,bound/coefficient)
        else:
            lower = bound/coefficient if lower is None else max(lower,bound/coefficient)
    if lower is not None and upper is not None and lower > upper:
        return None
    assert lower is not None
    return dict(F_coefficient=af,B_coefficient=bb,rhs_exact=str(rhs),rhs_RUB=number(rhs),
                parameter=parameter,parameter_min_exact=str(lower),
                parameter_max_exact=str(upper) if upper is not None else 'UNBOUNDED',
                F_at_min=number(x0+x1*lower),B_at_min=number(y0+y1*lower),
                F_at_max=number(x0+x1*upper) if upper is not None else None,
                B_at_max=number(y0+y1*upper) if upper is not None else None)


def finite_checks():
    summary=table('runs/portfolio_v2/summary.csv',BASE)
    union=table('runs/final_variants_v1/network_union.csv',BASE)
    for name in ['runs/portfolio_v2/summary.csv','runs/final_variants_v1/network_union.csv']:
        check('subject retains exact ba9 input '+name,blob(BASE,P+name)==blob(SUBJECT,P+name))
    receipt=obj('runs/budget_choice_v1/input_receipt.json')
    check('two exact input receipts',len(receipt['files'])==2)
    for r in receipt['files']:
        check('input receipt hash '+r['path'],r['source_commit']==BASE and r['sha256']==hashlib.sha256(blob(BASE,P+r['path'])).hexdigest())
    unionmap={r['portfolio']:r for r in union}
    singleton={r['portfolio']:r for r in union if int(r['component_count'])==1}
    gate_rows=[]
    for r in union:
        parts=r['portfolio'].split('+')
        pairs=set().union(*(set(singleton[n]['airport_pairs'].split(';')) for n in parts))
        check('unordered distinct pair union '+r['portfolio'],
              len(pairs)==int(r['unique_model_airport_pairs']) and
              pairs==set(r['airport_pairs'].split(';')) and
              all(p=='-'.join(sorted(p.split('-'))) for p in pairs))
        working=sum(int(singleton[n]['working_allocated']) for n in parts)
        newbase=int(any(n.startswith('H_UFA') for n in parts))
        check('resource/base lineage '+r['portfolio'],working==int(r['working_allocated']) and newbase==int(r['new_UFA_base_count']) and r['reserve_assumption']=='1')
        check('no operating acceptance '+r['portfolio'],r['accepted_operating_routes']=='' and r['actual_available_aircraft']=='' and r['complete_case_acceptance']=='False')
        gate_rows.append(dict(candidate=r['portfolio'],union_source_line=union.index(r)+2,
                              unique_unordered_pairs=len(pairs),sum_component_pair_counts=sum(int(singleton[n]['unique_model_airport_pairs'])for n in parts),
                              working=working,n=working+1,b=newbase,working_gate=working<=4,
                              count_gate=8<=len(pairs)<=12,additional_newbase_gate=newbase==1,
                              operating_accepted=False))
    save('independent_gate_counts.csv',gate_rows)
    groups=collections.defaultdict(list)
    source_money=[]
    for line,r in enumerate(summary,2):
        key=r['capture_law'],r['scenario']
        u=unionmap[r['portfolio']]
        working=int(u['working_allocated']);base=int(u['new_UFA_base_count'])
        check('summary metadata row '+str(line),working==int(r['working_required']) and base==int(r['new_UFA_base_count']) and r['reserve_assumption']=='1' and r['numerical_price_period']=='CIRI_NET_RUB_WEEK_20261207_13' and r['full_budget']=='')
        c=Q(r['gross_revenue'])-Q(r['foregone_RW_revenue'])-Q(r['flight_variable_cost'])-Q(r['new_pax_variable'])+Q(r['saved_old_pax_variable'])
        check('money bridge row '+str(line),close(c,r['contribution_before_base_fleet_opportunity']))
        source_money.append(dict(source_line=line,candidate=r['portfolio'],capture_law=key[0],scenario=key[1],
                                 source_C=r['contribution_before_base_fleet_opportunity'],recomputed_C=number(c),
                                 difference_RUB=number(c-Q(r['contribution_before_base_fleet_opportunity'])),
                                 includes_foregone_revenue_once=True,includes_saved_old_cost_once=True))
        groups[key].append(dict(name=r['portfolio'],c=Q(r['contribution_before_base_fleet_opportunity']),n=working+1,b=base,
                                pairs=int(u['unique_model_airport_pairs']),source_line=line,union_line=union.index(u)+2))
    save('independent_source_money.csv',source_money)
    observed=table('runs/budget_choice_v1/candidate_domains.csv')
    observedmap={(r['case_id'],r['candidate']):r for r in observed}
    observedineq=table('runs/budget_choice_v1/pairwise_inequalities.csv')
    imap={(r['case_id'],r['candidate'],r['alternative']):r for r in observedineq}
    observedex=table('runs/budget_choice_v1/pre_economic_exclusions.csv')
    exmap={(r['case_id'],r['candidate']):r for r in observedex}
    domains={};certificates=[];vertex_rows=[];bounds=[];ineq=[];witness_rows=[];ind_candidates=[];excluded=[]
    for (law,sc),source in sorted(groups.items()):
        for domain in DOMAINS:
            cid='|'.join((law,sc,domain))
            eligible=[]
            for a in source:
                reasons=[]
                if a['n']-1>4:reasons.append('WORKING_LABELS_GT4')
                if domain!=DOMAINS[0] and not 8<=a['pairs']<=12:reasons.append('MODEL_PAIR_COUNT_OUTSIDE8_12')
                if domain==DOMAINS[2] and a['b']!=1:reasons.append('NO_NEW_UFA_BASE')
                if reasons:
                    e=exmap[cid,a['name']]
                    check('exclusion '+cid+'|'+a['name'],e['reason']==';'.join(reasons) and int(e['model_pairs'])==a['pairs'] and int(e['working'])==a['n']-1)
                    excluded.append(dict(case_id=cid,candidate=a['name'],reason=';'.join(reasons)))
                else:eligible.append(a)
            domains[cid]=eligible
            check('eligible count '+cid,len(eligible)==[7,5,3][DOMAINS.index(domain)])
            for a in eligible:
                r=observedmap[cid,a['name']]
                check('candidate source '+cid+'|'+a['name'],Q(r['C'])==a['c'] and int(r['n'])==a['n'] and int(r['b'])==a['b'] and int(r['model_pairs'])==a['pairs'] and int(r['candidate_count'])==len(eligible))
                check('unknown costs retained '+cid+'|'+a['name'],r['actual_F']==r['actual_B']==r['full_PnL']=='' and r['launch_accepted']=='False')
                vv=vertices(planes(a,eligible))
                ds=[b for b in eligible if b['name']!=a['name'] and b['c']>a['c'] and b['n']<=a['n'] and b['b']<=a['b']]
                check('exact feasible or direct dominance '+cid+'|'+a['name'],bool(vv)!=bool(ds))
                check('owner active classification '+cid+'|'+a['name'],bool(vv)==bool(r['witness_F']))
                if vv:
                    check('active state '+cid+'|'+a['name'],r['state']=='POSSIBLE_BEST_OR_TIED_WITHIN_ENUMERATED_ACTIONS')
                    f0,b0=Q(r['witness_F']),Q(r['witness_B'])
                    check('owner nonnegative witness '+cid+'|'+a['name'],f0>=0 and b0>=0)
                    for b in eligible:
                        margin=score(a,f0,b0)-score(b,f0,b0)
                        check('owner witness vs '+cid+'|'+a['name']+'|'+b['name'],margin>=-TOL)
                        witness_rows.append(dict(case_id=cid,candidate=a['name'],alternative=b['name'],
                                                 F=r['witness_F'],B=r['witness_B'],independent_slack_RUB=number(margin)))
                    for f,b in vv:
                        vertex_rows.append(dict(case_id=cid,candidate=a['name'],F_exact=str(f),B_exact=str(b),F=number(f),B=number(b)))
                else:
                    check('dominance names '+cid+'|'+a['name'],set(r['dominators'].split(';'))=={b['name']for b in ds})
                    d=ds[0]
                    certificates.append(dict(case_id=cid,candidate=a['name'],dominator=d['name'],
                                              positive_constant_exact=str(d['c']-a['c']),
                                              positive_constant_RUB=number(d['c']-a['c']),
                                              F_coefficient=a['n']-d['n'],B_coefficient=a['b']-d['b'],
                                              formula='J_dominator-J_candidate=positive_constant+F_coefficient*F+B_coefficient*B; strictly positive for every F,B>=0'))
                ind_candidates.append(dict(case_id=cid,candidate=a['name'],source_summary_line=a['source_line'],source_union_line=a['union_line'],
                                           C_exact=str(a['c']),n=a['n'],b=a['b'],pairs=a['pairs'],
                                           independently_possible_best_or_tied=bool(vv),vertex_count=len(vv),KEEP_dominates_under_equal_terms=a['c']<0))
                for b in eligible:
                    if a['name']==b['name']:continue
                    af,bb,rhs=a['n']-b['n'],a['b']-b['b'],a['c']-b['c']
                    z=imap[cid,a['name'],b['name']]
                    check('pair inequality '+cid+'|'+a['name']+'|'+b['name'],int(z['F_coefficient'])==af and int(z['B_coefficient'])==bb and close(rhs,z['rhs_RUB_per_week']))
                    ineq.append(dict(case_id=cid,candidate=a['name'],alternative=b['name'],F_coefficient=af,B_coefficient=bb,rhs_exact=str(rhs),rhs_RUB=number(rhs)))
            for a,b in itertools.combinations(eligible,2):
                edge=tie_edge(a,b,eligible)
                if edge:bounds.append(dict(case_id=cid,candidate=a['name'],alternative=b['name'],**edge))
    check('18 problems 90 rows 408 inequalities 39 feasible 51 dominated 180 exclusions',
          (len(domains),len(ind_candidates),len(ineq),len(ind_candidates)-len(certificates),len(certificates),len(excluded))==(18,90,408,39,51,180))
    check('no owner candidate or inequality duplicates',len(observedmap)==len(observed)==90 and len(imap)==len(observedineq)==408 and len(exmap)==len(observedex)==180)
    save('independent_candidates.csv',ind_candidates);save('independent_pairwise_inequalities.csv',ineq)
    save('independent_dominance_certificates.csv',certificates);save('independent_region_vertices.csv',vertex_rows)
    save('independent_all_boundaries.csv',bounds);save('independent_exclusions.csv',excluded)
    save('independent_witness_slacks.csv',witness_rows)
    ow=table('runs/budget_choice_v1/feasible_witnesses.csv')
    wm={(r['case_id'],r['candidate'],r['alternative']):r for r in witness_rows}
    check('201 serialized witness comparisons complete',len(ow)==len(wm)==201)
    for w in ow:
        cid=w['case_id'];a=next(x for x in domains[cid] if x['name']==w['candidate']);b=next(x for x in domains[cid] if x['name']==w['alternative'])
        f,beta=Q(w['witness_F']),Q(w['witness_B'])
        check('serialized witness arithmetic '+cid+'|'+a['name']+'|'+b['name'],
              (cid,a['name'],b['name']) in wm and close(score(a,f,beta),w['candidate_adjusted']) and close(score(b,f,beta),w['alternative_adjusted']) and close(score(a,f,beta)-score(b,f,beta),w['slack_RUB']))
    return domains,bounds


def boundary_and_term_checks(domains,bounds):
    finals=[];sides=[];termrows=[];floors=[];counterexamples=[]
    terms=table('runs/budget_choice_v1/new_base_constraint_terms.csv')
    floor=table('runs/budget_choice_v1/new_base_constraint_floor.csv')
    for cid,actions in domains.items():
        law,sc,domain=cid.split('|')
        check('all actions negative over entire orthant '+cid,all(a['c']<0 and a['n']>=0 and a['b']>=0 for a in actions))
        if domain==DOMAINS[0]:continue
        if domain==DOMAINS[1]:an,bn='D_previous_best8','D_SVX8'
        else:an,bn='H_UFA_8','D_SVX8+H_UFA_4'
        a=next(x for x in actions if x['name']==an);b=next(x for x in actions if x['name']==bn)
        threshold=(a['c']-b['c'])/(a['n']-b['n'])
        check('B cancels '+cid,a['b']==b['b'])
        edges=[x for x in bounds if x['case_id']==cid]
        check('entire final frontier recovered '+cid,len(edges)==1 and {edges[0]['candidate'],edges[0]['alternative']}=={an,bn} and Q(edges[0]['rhs_exact'])/edges[0]['F_coefficient']==threshold and edges[0]['parameter']=='B' and edges[0]['parameter_min_exact']=='0' and edges[0]['parameter_max_exact']=='UNBOUNDED')
        finals.append(dict(case_id=cid,lower_F_action=an,higher_F_action=bn,F_threshold_exact=str(threshold),F_threshold_RUB=number(threshold),B_domain='all B>=0',tie='BOTH_ACTIONS_RETAINED_AT_EQUALITY'))
        for beta in [Q(0),Q(1000000),Q(10**12)]:
            for delta in [Q(-1),Q(0),Q(1)]:
                f=threshold+delta
                values={x['name']:score(x,f,beta) for x in actions};maximum=max(values.values())
                winners=sorted(k for k,v in values.items() if v==maximum)
                expected=[an] if delta<0 else [bn] if delta>0 else sorted([an,bn])
                check('boundary tie/sides '+cid+'|'+str(beta)+'|'+str(delta),winners==expected)
                sides.append(dict(case_id=cid,F_exact=str(f),B_exact=str(beta),offset_RUB=number(delta),winners=';'.join(winners),KEEP=0,best_J=number(maximum)))
        if domain==DOMAINS[2]:
            # A positive incremental cost of candidate A shifts F threshold down.
            extra=Q(1000000);correct=threshold-extra/(a['n']-b['n']);probe=(threshold+correct)/2
            check('unequal costs can reverse choice '+cid,score(a,probe,0)>score(b,probe,0) and score(a,probe,0)-extra<score(b,probe,0))
            counterexamples.append(dict(type='UNEQUAL_OTHER_COST_SIGN',case_id=cid,O_candidate_minus_O_alternative=number(extra),
                                        old_F_threshold=number(threshold),correct_F_threshold=number(correct),
                                        wrong_sign_threshold=number(threshold+extra/(a['n']-b['n'])),
                                        probe_F=number(probe),equal_O_winner=an,actual_winner_with_extra_cost=bn,
                                        formula='(nA-nB)F+(bA-bB)B+(OA-OB)<=CA-CB'))
    for law in sorted({cid.split('|')[0]for cid in domains}):
        for sc in ['base','cautious']:
            unrestricted=domains['|'.join([law,sc,DOMAINS[1]])]
            restricted=domains['|'.join([law,sc,DOMAINS[2]])]
            baseline=next(x for x in unrestricted if x['name']=='D_previous_best8')
            for a in restricted:
                constant=baseline['c']-a['c'];fc=a['n']-baseline['n'];bc=a['b']-baseline['b']
                r=next(t for t in terms if(t['capture_law'],t['scenario'],t['restricted_candidate'])==(law,sc,a['name']))
                check('term witness '+law+'|'+sc+'|'+a['name'],close(constant,r['baseline_minus_candidate_constant']) and fc==int(r['F_coefficient']) and bc==int(r['B_coefficient']) and constant>0 and fc>=0 and bc==1)
                termrows.append(dict(capture_law=law,scenario=sc,baseline=baseline['name'],candidate=a['name'],constant_exact=str(constant),constant_RUB=number(constant),F_coefficient=fc,B_coefficient=bc))
            minimum=min(baseline['c']-a['c'] for a in restricted)
            r=next(t for t in floor if(t['capture_law'],t['scenario'])==(law,sc))
            check('floor all F/B via nonnegative coefficients '+law+'|'+sc,close(minimum,r['lower_bound_RUB_per_week_at_B0']) and r['additional_B_coefficient']=='1' and r['actual_base_cost']=='')
            for f,beta in itertools.product([Q(0),Q(1000000),Q(10**10)],repeat=2):
                difference=max(score(a,f,beta)for a in unrestricted)-max(score(a,f,beta)for a in restricted)
                check('floor numeric corroboration '+law+'|'+sc+'|'+str(f)+'|'+str(beta),difference>=minimum+beta)
            floors.append(dict(capture_law=law,scenario=sc,lower_bound_exact=str(minimum),lower_bound_RUB=number(minimum),B_coefficient=1,
                               sharp_at_F0_B0=True,meaning='finite-set additional-constraint effect, not base opening cost or actual RW loss'))
    check('18 terms 6 floors',len(terms)==len(termrows)==18 and len(floor)==len(floors)==6)
    general_points=[]
    for edge in bounds:
        cid=edge['case_id'];actions=domains[cid]
        a=next(x for x in actions if x['name']==edge['candidate'])
        b=next(x for x in actions if x['name']==edge['alternative'])
        lo=Q(edge['parameter_min_exact'])
        hi=Q(edge['parameter_max_exact'])if edge['parameter_max_exact']!='UNBOUNDED'else None
        probes=[lo,(lo+hi)/2,hi]if hi is not None else[lo,lo+Q(1000000)]
        for t in dict.fromkeys(probes):
            if edge['parameter']=='F':
                f=t;beta=(Q(edge['rhs_exact'])-edge['F_coefficient']*f)/edge['B_coefficient']
            else:
                beta=t;f=(Q(edge['rhs_exact'])-edge['B_coefficient']*beta)/edge['F_coefficient']
            values={x['name']:score(x,f,beta)for x in actions};maximum=max(values.values())
            winners=sorted(k for k,v in values.items()if v==maximum)
            check('all-boundary exact tie '+cid+'|'+a['name']+'|'+b['name']+'|'+str(t),a['name']in winners and b['name']in winners and f>=0 and beta>=0)
            general_points.append(dict(case_id=cid,F_exact=str(f),B_exact=str(beta),winners=';'.join(winners),all_alternatives_checked=True))
    save('independent_general_boundary_points.csv',general_points)
    # A real arithmetic counterexample to recharging a cost already in source C.
    source=table('runs/portfolio_v2/summary.csv',BASE)
    a=next(x for x in source if x['portfolio']=='D_previous_best8'and x['scenario']=='base'and x['capture_law']=='COUNT_ALL_OFFERS')
    b=next(x for x in source if x['portfolio']=='D_SVX8'and x['scenario']=='base'and x['capture_law']=='COUNT_ALL_OFFERS')
    ca,cb=Q(a['contribution_before_base_fleet_opportunity']),Q(b['contribution_before_base_fleet_opportunity'])
    correct=ca-cb
    wrong=(ca-Q(a['flight_variable_cost']))-(cb-Q(b['flight_variable_cost']))
    check('double-charged source flight cost changes boundary',correct!=wrong)
    counterexamples.append(dict(type='ACTUAL_SOURCE_DOUBLE_COST_COUNTEREXAMPLE',scenario='base',
                                candidate='D_previous_best8',alternative='D_SVX8',
                                correct_F_boundary_RUB=number(correct),
                                wrong_boundary_if_flight_cost_deducted_twice_RUB=number(wrong),
                                duplicated_candidate_cost_RUB=a['flight_variable_cost'],duplicated_alternative_cost_RUB=b['flight_variable_cost'],
                                meaning='flight cost already subtracted in C; only new uncounted incremental articles belong in F/B/O'))
    # Synthetic named-donor receipt: a signed +1m already reconciled into a C-like delta is not charged again.
    donor=Q(1000000);f=correct+donor/2
    before=ca-3*f-(cb-2*f);with_donor=before+donor
    check('one donor delta can reverse a finite choice',before<0 and with_donor>0 and before+2*donor!=with_donor)
    counterexamples.append(dict(type='SYNTHETIC_NAMED_DONOR_ACCOUNTING',observed_donor=False,
                                F=number(f),signed_donor_gain_RUB=number(donor),
                                J_candidate_minus_alternative_without_donor_RUB=number(before),
                                correct_difference_once_RUB=number(with_donor),
                                wrong_difference_if_same_gain_added_twice_RUB=number(before+2*donor),
                                alternative_O_extension='O_candidate-O_alternative=-1000000',
                                meaning='One externally supported KEEP/action donor delta; actual donor remains UNKNOWN'))
    # Count: directions/components would admit a four-pair pilot or miscount a shared pair.
    u=table('runs/final_variants_v1/network_union.csv',BASE)
    for name in ['H_UFA_4','D_SVX8+D_previous_best8','H_UFA_4+H_UFA_8']:
        x=next(r for r in u if r['portfolio']==name)
        counterexamples.append(dict(type='COUNT_UNIT',candidate=name,unique_unordered_pairs=int(x['unique_model_airport_pairs']),
                                    directed_pair_count=2*int(x['unique_model_airport_pairs']),component_sum=int(x['sum_component_pair_counts']),
                                    working=int(x['working_allocated']),correct_joint_gate=x['joint_model_gates_pass']))
    # Omitting a common reserve shifts absolute action deltas, even when pairwise choices cancel it.
    counterexamples.append(dict(type='COMMON_RESERVE_AND_DOUBLE_COST',F=1000000,
                                omitting_one_incremental_reserve_overstates_each_J_RUB=1000000,
                                pairwise_F_threshold_impact=0,
                                warning='Do not add crew/MRO/foregone-RW-revenue already inside C to F/B/O; F/B/O are incremental uncounted terms only'))
    save('independent_final_boundaries.csv',finals);save('independent_boundary_sides.csv',sides)
    save('independent_constraint_terms.csv',termrows);save('independent_constraint_floors.csv',floors)
    save('counterexamples.json',counterexamples)


def projection_checks():
    name='inputs/model-repair-001/proposed_common_view/evaluation_summary.csv'
    src=table(name);projection=table('runs/final_model_projection_v1/source_results.csv')
    original_path='context/23_night_run_20261110/model_repair/proposed_common_view/evaluation_summary.csv'
    origin=blob('27740ffea0821aa404ecd1013d1bb141613261f3',original_path)
    check('projection exact original package bytes',origin==blob(SUBJECT,P+name))
    check('58 projection rows',len(src)==len(projection)==58)
    parameters=table('inputs/model-repair-001/proposed_common_view/parameter_registry.csv')
    weeks={r['scenario_id']:r['value']for r in parameters if r['parameter']=='weeks_per_year'}
    check('annualization labels have source parameter',weeks=={'base':'52','cautious':'48'})
    details=[];counts=collections.Counter()
    author={(r['model_id'],r['candidate_id'],r['scenario_id']):r for r in src if r['run_id']=='AUTHOR_REPLAY'}
    for line,(r,t) in enumerate(zip(src,projection),2):
        annual=r['model_id'].startswith('anastasia')
        fields=('annual_contribution_before_base_fleet_opportunity_rub','annual_trips','annual_segments') if annual else ('contribution_before_base_fleet_opportunity','sold_journeys','segment_pax')
        run=r['run_id']
        semantic='AUTHOR_REPLAY' if run=='AUTHOR_REPLAY' else 'CORRECTED_REPLAY_STRUCTURAL_D_GUARD_CURRENT_DELTA_ZERO' if run=='CORRECTED_MARKET_BOUND_ONLY' else 'COMMON_COMPARISON_PROPOSED_QF_POLICY_NOT_MANDATORY_REPAIR'
        counts[semantic]+=1
        pairs={'model_id':'model_id','candidate':'candidate_id','scenario':'scenario_id','original_run_id':'run_id',
               'original_mode':'mode','original_source_commit':'source_commit','source_input_set':'input_set_id',
               'display_profile':'profile','source_profile':'source_profile','source_network':'source_network','money_definition':'money_definition',
               'contribution_rub':fields[0],'endpoint_journeys':fields[1],'passenger_segments':fields[2]}
        check('projected strings line '+str(line),all(t[a]==r[b] for a,b in pairs.items()) and t['source_csv_line']==str(line) and t['source_money_field']==fields[0])
        expected_group=('ANASTASIA_ANNUAL_'if annual else'CIRI_CONTEXT21_WEEK_')+r['scenario_id']
        check('projection lineage/group line '+str(line),t['comparison_group']==expected_group and t['source_csv']==name and t['received_package_commit']=='27740ffea0821aa404ecd1013d1bb141613261f3')
        period=('SYNTHETIC_YEAR_'+weeks[r['scenario_id']]+'_WEEKS')if annual else r['period_start']+'/'+r['period_end']
        check('period/resource/money units line '+str(line),t['period']==period and t['working_ceiling']==('9'if annual else'4') and t['reserve_ceiling']=='1' and r['currency']=='RUB' and r['resource_envelope_id']==('ANASTASIA_9_WORKING_PLUS_1_RESERVE'if annual else'CIRI_4_WORKING_PLUS_1_RESERVE'))
        check('policy and no cross-group rank line '+str(line),t['semantic_mode']==semantic and t['numerical_cross_group_comparison_allowed']=='False' and t['full_budget']==t['actual_paid_OD']==t['net_new_RW_observed']=='' and t['policy_acceptance']==('AGENT_PROPOSAL'if semantic.startswith('COMMON_')else'NOT_TEAM_STRATEGY_ACCEPTANCE'))
        if run=='CORRECTED_MARKET_BOUND_ONLY':
            baseline=author['anastasia_network_author',r['candidate_id'],r['scenario_id']]
            check('D guard current zero line '+str(line),all(r[f]==baseline[f]for f in fields))
        details.append(dict(source_line=line,model_id=r['model_id'],run_id=run,candidate=r['candidate_id'],scenario=r['scenario_id'],
                            semantic_mode=semantic,period=period,resource_envelope=r['resource_envelope_id'],
                            currency=r['currency'],source_price_basis=r['price_basis'],source_tax_basis=r['tax_basis'] or 'UNKNOWN',
                            money_definition=r['money_definition'],original_contribution_string=r[fields[0]],numeric_strings_match=True))
    check('20 author / 2 guard / 36 proposed',sorted(counts.values())==[2,20,36])
    save('independent_projection.csv',details)
    # Frontier scope is checked against the supplied independent review, not re-executed here.
    receipt=obj('inputs/frontier-review-001/receipt.json')
    for r in receipt['files']:
        delivered=blob(SUBJECT,P+r['path']);upstream=blob(r['source_commit'],r['source_path'])
        check('frontier review exact bytes '+r['path'],delivered==upstream and hashlib.sha256(delivered).hexdigest()==r['sha256'])
    hand=obj('inputs/frontier-review-001/handoff.json')
    matrix=table('runs/admission_v3/acceptance_matrix.csv');front=next(r for r in matrix if r['artifact']=='hypothesis_frontier')
    check('frontier admission bounded',hand['verdict']=='APPROVE_SCOPED' and hand['delivered']['all35_preserved'] and hand['delivered']['untested_preserved']==32 and front['review_commit']=='58a02028e062b1abd803d99e19f630b75ec80657' and front['verdict']=='APPROVE_SCOPED_EXACT_519998' and 'source/paidmarket/actualresource/fullbudget' in front['does_not_approve'])
    save('frontier_scope_check.json',dict(status='PASS_LINEAGE_AND_SCOPE_ONLY',supplied_review=receipt['source_commit'],
                                        personal_calendar_reexecution=False,all35_preserved=True,untested=32,
                                        acceptance='calendar/capacity/mechanical only',source_market_resource_fullbudget='UNKNOWN_NOT_PROMOTED'))


def preservation_checks():
    names=git('ls-tree','-r','--name-only',BASE,P).decode().splitlines()
    frozen=[n for n in names if n.startswith(tuple(P+x+'/' for x in ['inputs','runs','analysis']))]
    result=[]
    for n in frozen:
        a,b=blob(BASE,n),blob(SUBJECT,n)
        check('frozen bytes '+n,a==b)
        result.append(dict(path=n,base_commit=BASE,subject_commit=SUBJECT,bytes=len(a),sha256=hashlib.sha256(a).hexdigest(),identical=a==b))
    check('381 prior frozen blobs',len(result)==381)
    save('independent_byte_preservation.csv',result)
    manifest=obj('output_manifest.json')
    for r in manifest['files']:
        data=blob(SUBJECT,P+r['path'])
        check('owner output manifest '+r['path'],len(data)==r['bytes'] and hashlib.sha256(data).hexdigest()==r['sha256'])
    save('owner_manifest_check.json',dict(status='PASS',entries=len(manifest['files']),commit=SUBJECT,
                                        acceptance='Git bytes only; not primary-source verification'))


def determinism_checks():
    runtime=OUT/'_runtime'
    check('runtime initially absent',not runtime.exists())
    root=runtime/P
    necessary=['common_demand.py','budget_choice_contract.json','budget_choice_domains.py',
               'final_model_projection.py','update_acceptance_v7.py','render_budget_choice_chart.py',
               'runs/portfolio_v2/summary.csv','runs/final_variants_v1/network_union.csv',
               'inputs/model-repair-001/proposed_common_view/evaluation_summary.csv',
               'runs/admission_v2/acceptance_matrix.csv']
    try:
        for n in necessary:
            target=root/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob(SUBJECT,P+n))
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        logs=[]
        for script in ['budget_choice_domains.py','final_model_projection.py','update_acceptance_v7.py','render_budget_choice_chart.py']:
            done=subprocess.run([sys.executable,str(root/script)],cwd=runtime,env=env,capture_output=True,text=True)
            logs.append(dict(script=script,returncode=done.returncode,stdout=done.stdout,stderr=done.stderr))
            check('isolated owner replay '+script,done.returncode==0,done.stderr)
        output=[]
        for directory in ['runs/budget_choice_v1','runs/final_model_projection_v1','runs/admission_v3']:
            for f in sorted((root/directory).iterdir()):
                name=f.relative_to(root).as_posix();expected=blob(SUBJECT,P+name);actual=f.read_bytes()
                check('deterministic new output '+name,expected==actual)
                output.append(dict(path=name,bytes=len(actual),sha256=hashlib.sha256(actual).hexdigest(),byte_identical=True))
        check('13 exact new deterministic outputs',len(output)==13)
        # An actual input mutation is rejected by owner code before replacing outputs.
        target=root/'runs/portfolio_v2/summary.csv'
        original=target.read_bytes();target.write_bytes(original.replace(b'-7326330.91171322',b'-7326331.91171322',1))
        check('mutation actually changed bytes',target.read_bytes()!=original)
        done=subprocess.run([sys.executable,str(root/'budget_choice_domains.py')],cwd=runtime,env=env,capture_output=True,text=True)
        check('actual source mutation rejected',done.returncode!=0 and 'input drift' in done.stderr and 'runs/portfolio_v2/summary.csv' in done.stderr)
        mutation=dict(returncode=done.returncode,stderr=done.stderr,mutation='C for D_SVX8/base changed by -1 RUB in isolated snapshot only',rejected=True)
        for row in output:
            check('mutation leaves outputs intact '+row['path'],hashlib.sha256((root/row['path']).read_bytes()).hexdigest()==row['sha256'])
        save('owner_replay_log.json',logs);save('independent_determinism.csv',output);save('source_mutation_check.json',mutation)
        import scipy
        save('execution_environment.json',dict(python=sys.version,scipy=scipy.__version__,new_dependencies_installed=False,
                                               independent_arithmetic='fractions.Fraction; exhaustive halfplane vertices and exact tie intervals',
                                               owner_replay='separate disposable pinned snapshot; no owner live writes',runtime_removed=True))
    finally:
        if runtime.exists():shutil.rmtree(runtime)


def main():
    blob(ROOT_PIN,'context/23_night_run_20261110/contract.md')
    blob(ROOT_PIN,'context/23_night_run_20261110/briefs/budget_choice_review.md')
    for n in ['budget_choice_contract.json','budget_choice_domains.py','budget_choice_readout.md',
              'final_model_projection.py','model_comparison.md','reproduce.md','update_acceptance_v7.py',
              'portfolio_comparison.py','final_variant_synthesis.py','common_demand.py','portfolio_guard_contract.json',
              'decisions.json','acceptance_events.json','checks/v7_replay.json']:
        blob(SUBJECT,P+n)
    domains,bounds=finite_checks()
    boundary_and_term_checks(domains,bounds)
    projection_checks()
    preservation_checks()
    determinism_checks()
    save('source_manifest.json',dict(subject_commit=SUBJECT,source_cutoff_msk='2026-11-10T08:30:00+03:00',
                                     policy='all content inputs read with git show exact SHA; no live owner folders',
                                     files=sorted(READS.values(),key=lambda r:(r['source_commit'],r['path']))))
    save('checks.json',dict(status='PASS',personal_checks_passed=len(CHECKS),checks=CHECKS,
                            counts=dict(choice_problems=18,candidate_domain_rows=90,pairwise_inequalities=408,
                                        feasible_candidates=39,direct_dominance_certificates=51,witness_comparisons=201,
                                        terms=18,floors=6,projection_rows=58,preserved_old_blobs=381,new_deterministic_outputs=13),
                            numerical_tolerance_RUB=str(TOL),exact_region_arithmetic=True))
    print(json.dumps(dict(status='PASS',personal_checks=len(CHECKS),read_blobs=len(READS),runtime_removed=not(OUT/'_runtime').exists())))


if __name__=='__main__':main()
