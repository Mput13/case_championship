#!/usr/bin/env python3
"""Execute P38 completed old/mixed full-month economics. Writes ONLY here.

Run with context/28_end_to_end_audit_20261110/code/sandbox/venv/bin/python -B.
The completed mixed-programme generator is an admitted read-only input.
No old builders, exporters, verify entry points, Git or network are invoked.
"""
import sys
sys.dont_write_bytecode=True
import calendar
import copy
import csv
import json
import math
from collections import Counter,defaultdict
from datetime import datetime,timedelta
from pathlib import Path
import core as C

HERE=C.HERE
CONFIG=C.js(HERE/'config.json')

def dump(name,x):
    (HERE/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+'\n')

def table(name,rows,fields=None):
    rows=list(rows)
    fs=fields or list(dict.fromkeys(k for r in rows for k in r))
    with (HERE/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fs);w.writeheader()
        for r in rows:
            w.writerow({k:('NULL' if v is None else C.canonical(v) if isinstance(v,(dict,list,tuple)) else
                round(v,8) if isinstance(v,float) else v) for k,v in r.items()})

def source_manifest():
    paths=[C.P38/'TASK.md',C.P38/'source_pins.json',C.P38/'protected_files.json',
        C.P38/'source_gate_for_calculation.md']
    for folder,names in {
        'contract':['common_contract.json','resource_contract.json','month_adapter.py','engine_handoff.md',
                    'pair_universe.csv','programme_inventory.csv','monthly_input_audit.csv','source_manifest.json','validation.json'],
        'market_admission':['canonical_pairs.csv','canonical_services.csv','canonical_fares.csv','monthly_evidence.csv',
                            'sources.csv','source_admission.csv','validation.json'],
        'cost_admission':['canonical_cost_items.csv','support_conditions.csv','commercial_options.csv',
                          'ground_overlap.csv','reserve_launch_costs.csv','sources.csv','source_admission.csv','validation.json']
    }.items():
        paths.extend(C.P38/folder/n for n in names)
    paths.extend(C.P36/'pass2'/n for n in ['candidate_results.csv','three_state_comparison.csv','equivalence_map.csv',
        'revenue_cost_ledger.csv','structural_cautious_bounds.csv','top5_pairs.csv'])
    paths.extend(C.P36/'pass1'/n for n in ['shortlist.csv','three_state_screen.csv'])
    paths.append(C.ROOT/'context/37_svx_kja_keep_check_20261112/calculation/break_even.csv')
    paths.extend([C.ROOT/'context/31_direct_growth_research_20261112/route_economics/calculate.py',
        C.ROOT/'context/34_new_direct_top5_20261112/calculation/calculate.py'])
    runtime=[]
    for g in C.js(C.P38/'contract/source_manifest.json')['runtime_groups']:
        for p in sorted((C.ROOT/g['path']).rglob('*')):
            if p.is_file() and p.suffix in g['extensions'] and '__pycache__' not in p.parts:runtime.append(p)
    if CONFIG.get('completed_programme_gate'):
        paths.extend(C.P38/'programmes'/n for n in ['engine_handoff.md','programme_specs.json','programme_catalog.csv','calendar_checks.csv','validation.json','input_manifest.json','search_coverage.json'])
    paths=sorted(set(paths+runtime))
    inputs={str(p.relative_to(C.ROOT)):C.sha(p) for p in paths}
    local={n:C.sha(HERE/n) for n in ['core.py','calculate.py','config.json','verify.py']}
    return dict(status='COMPLETED_CANONICAL_ONLY',input_sha256=inputs,code_sha256=local,
        input_digest=C.digest(inputs),code_digest=C.digest(local),guard=C.guard(),
        new_numeric_OD_updates=0,new_numeric_net_updates=0,new_actual_invoice_updates=0,
        live_programmes_read=False,completed_programmes_admitted=bool(CONFIG.get('completed_programme_gate')),old_builders_exporters_verify_invoked=False,
        formula_lineage='P31 pure costs/fare/mass/choice; P05 pinned carrier monthly profile; P06 exact allocation reference',
        market_evidence_not_frequency=True,public_rates_not_added_to_ground=True)

def action_rows(cid,t):
    k={j['id']:j for j in t['states']['KEEP']};w={j['id']:j for j in t['states']['WITHOUT_NEW']}
    out=[]
    for jid,j in k.items():
        q=w.get(jid)
        if q is None:action='REMOVE'
        elif C.semantic_jobs([j])==C.semantic_jobs([q]):action='RETAIN'
        elif j['tail']!=q['tail']:action='MOVE_OR_SWAP_TAIL'
        else:action='RETIME_OR_SWAP_CLOCK'
        out.append(dict(candidate=cid,cohort=t['cohort'],cohort_key=t['cohort_key'],old_id=jid,action=action,
            keep_tail=j['tail'],changed_tail=q['tail'] if q else None,
            keep_dep=min(f['dep'] for f in j['flights']),changed_dep=min(f['dep'] for f in q['flights']) if q else None,
            applied_identically_in='WITHOUT_NEW;REPLACE',cancellation_C='UNKNOWN' if action=='REMOVE' else 'not removal',
            cancellation_common_R_minus_W=True,actual_unmodelled_old_work=None))
    for jid,j in w.items():
        if jid not in k:raise ValueError('old ID silently changed:'+cid+'/'+jid)
    assert C.semantic_jobs(C.old(t['states']['REPLACE']),True)==C.semantic_jobs(t['states']['WITHOUT_NEW'],True)
    return out

def state_row(cid,t,m,sc,state,z,allz):
    k,w,r=(allz[s] for s in C.STATES)
    return dict(candidate=cid,cohort=t['cohort'],cohort_key=t['cohort_key'],month=f'2027-{m:02}',
        season=C.M.exposure(2027,m)['seasons'],scenario=sc,state=state,working_tails=len(t['tails'])-1,
        separate_R1=True,reserve_working=False,world_hash=C.WORLD_HASH(),primary='DIRECT_ONLY',through_journeys=0,
        known_subtotal_before_C_D_F=z['subtotal'],net_revenue=z['net_revenue'],variable_cost=z['variable_cost'],
        journeys=z['journeys'],new_leg_journeys=z['new_journeys'],retained_leg_journeys=z['retained_journeys'],
        internal_own_diverted_lower_bound=max(0,w['retained_journeys']-r['retained_journeys']) if state=='REPLACE' else None,
        net_new_to_RW_modelled=max(0,r['journeys']-w['journeys']) if state=='REPLACE' else None,
        external_own_diversion=None,departures=z['departures'],new_departures=z['new_departures'],
        paid_ferry_departures=z['ferry_departures'],BH=z['BH'],max_daily_BH=z['max_daily_BH'],
        BH8_diagnostics=z['BH8_diagnostics'],old_change_W_minus_K=w['subtotal']-k['subtotal'],
        new_R_minus_W=r['subtotal']-w['subtotal'],total_R_minus_K=r['subtotal']-k['subtotal'],
        score_definition='S1_CONFIG_AND_HANDOFF',
        F_plus_D_plus_uncovered_own_loss_plus_C=None,full_profit=None,cash=None,launch='NOT_AUTHORIZED_OR_PROVEN')

def pair_outputs(E,scores,menus):
    pairrows=C.read(C.P38/'contract/pair_universe.csv')
    market={r['pair']:r for r in C.read(C.P38/'market_admission/canonical_pairs.csv')}
    services=C.read(C.P38/'market_admission/canonical_services.csv')
    seeded={r['pair'] for r in pairrows}
    extra=defaultdict(list)
    for cid,t in C.templates().items():
        for j in C.new(t['states']['REPLACE']):
            for f in j['flights']:
                pp='-'.join(sorted((f['origin'],f['destination'])))
                if pp not in seeded:extra[pp].append((cid,f,t))
    for pp,events in sorted(extra.items()):
        a,b=pp.split('-');commercial=any(f['kind']=='SERVICE' for _,f,_ in events)
        pairrows.append(dict(pair=pp,airport_a=a,airport_b=b,
            classification='SOURCE_TEMPLATE_SERVICE_NO_MARKET_ADMISSION' if commercial else 'PAID_POSITIONING_ONLY',
            old_top5=False,AER_control=False,programmes=';'.join(sorted({cid for cid,_,_ in events})),
            service_directions=';'.join(sorted({f['origin']+'>'+f['destination'] for _,f,_ in events if f['kind']=='SERVICE'})),
            positioning_directions=';'.join(sorted({f['origin']+'>'+f['destination'] for _,f,_ in events if f['kind']=='PAID_FERRY'})),
            city_codec='-'.join(sorted((C.RE.city(a),C.RE.city(b)))),evidence_ref=events[0][2]['source']['source']))
        market[pp]=dict(own_rw_nonstop='UNKNOWN_EXTERNAL; modelled old jobs present where applicable',own_rw_source_ids='',
            market_competitors='UNKNOWN_NO_NEW_MARKET_ADMISSION',source_id='COMPLETED_LOCAL_TEMPLATE_ONLY',sourceurl='')
    preferred={'AER-SVX':'X_AER1','IKT-SVX':'X_SVX_IKT','KJA-SVX':'X_SVX_KJA',
        'CEK-MRV':'X_CEK_MRV_F','MRV-TJM':'X_TJM_MRV_F','GOJ-KJA':'X_GOJ_KJA_F'}
    pairs=[];thresholds=[]
    for p in pairrows:
        name=p['pair'];a,b=p['airport_a'],p['airport_b'];mk=market[name]
        qualified=[r for r in services if {r['origin'],r['destination']}=={a,b}]
        period=lambda r:'|'.join([r['origin']+'>'+r['destination'],r['carrier_operated'],r['flight'],r['valid_start'],r['valid_end'],r['source_id']])
        ownperiods=sorted({period(r) for r in qualified if 'WINGS' in r['carrier_operated'].upper() or r['flight'].replace('-','').startswith('WZ')})
        pairs.append(dict(pair=name,in_seed25=name in seeded,classification=p['classification'],old_top5=p['old_top5'],AER_control=p['AER_control'],
            commercial=p['classification']!='PAID_POSITIONING_ONLY',source_programmes=p['programmes'],
            service_directions=p['service_directions'],positioning_directions=p['positioning_directions'],
            reason='PAID_POSITIONING_CONTRACT: 0 seats/revenue, positive cost retained in entire closed chain' if
                p['classification']=='PAID_POSITIONING_ONLY' else 'CLOSED_CHAIN_SCENARIO; physical pair contribution is not separable chain profit',
            market_own_status=mk['own_rw_nonstop'],market_own_sources=mk['own_rw_source_ids'],
            own_published_direction_periods=ownperiods,
            admitted_supply_direction_periods=sorted({period(r) for r in qualified}),
            competing_supply=mk['market_competitors'],market_source_ids=mk['source_id'],source_url=mk['sourceurl'],
            evidence_rows_not_departures=len(qualified),fare_20kg_qualified=0,net_observed=None,endpoint_OD_observed=None,
            date_quality='source-specific periods; expired Dec2026 never extrapolated to Feb/summer2027',
            true_own_newness='UNPROVED',physical_source=p['evidence_ref'],MOW_pool=p['city_codec'],
            own_external_loss_gate='UNKNOWN even if no qualified current own row',
            final_status=CONFIG['programme_admission']))
        for origin,dest in ((a,b),(b,a)):
            # Select source templates that actually SELL the physical direction;
            # negative old60 templates remain available for the opposite triangle.
            choices=[]
            for cid,t in C.templates().items():
                nn=C.new(t['states']['REPLACE'])
                ff=[f for j in nn for f in j['flights']]
                if any(f['origin']==origin and f['destination']==dest and f['kind']!='PAID_FERRY' for f in ff):
                    choices.append((cid,t,ff))
            pref=preferred.get(name)
            choices.sort(key=lambda x:(0 if x[0]==pref else 1,
                len(C.new(x[1]['states']['REPLACE'])),len(x[2]),x[0]))
            for m in range(1,13):
                for sc in CONFIG['scenarios']:
                    common=dict(pair=name,physical_direction=origin+'>'+dest,city_direction=C.RE.city(origin)+'>'+C.RE.city(dest),
                        month=f'2027-{m:02}',scenario=sc,other_OD_fixed=True,actual_endpoint_OD=None,actual_net=None,
                        qualified_fare_count=0,market_sources=mk['source_id'],source=p['evidence_ref'],
                        own_published_direction_periods=ownperiods,
                        global_menu_complete=False,unknown_F_D_C_own_R1='combined differential deduction; not separate budgets',
                        cancellation_comparison='all menu scores before unknown C; different removal sets need their differential C')
                    if p['classification']=='PAID_POSITIONING_ONLY' or not choices:
                        thresholds.append(common|dict(status='PAID_POSITIONING_ONLY' if p['classification']=='PAID_POSITIONING_ONLY' else
                            'DIRECTION_NOT_IN_COMPLETED_COMMERCIAL_TEMPLATES',candidate=None,required_potential=None,
                            required_net=None,headroom=None,reason='No marketed seats; paid whole-chain ferry cost is preserved' if
                            p['classification']=='PAID_POSITIONING_ONLY' else 'Need source-based commercial closed programme; no phantom opposite-direction sale'))
                        continue
                    cid,t,_=choices[0];target=scores[cid,m,sc,'REPLACE'];key=(C.RE.city(origin),C.RE.city(dest))
                    aa=[]
                    for item in menus[t['cohort_key']]:
                        z=E.score(item['jobs'],item['tails'],m,sc)
                        if z['semantic']!=target['semantic']:
                            aa.append((item['candidate']+'/'+item['state'],z))
                    if not aa:raise ValueError('missing alternative')
                    inv=C.inverse_direction(target,aa,key);net=C.inverse_net(target,aa,key)
                    admission_alt=[('KEEP',scores[cid,m,sc,'KEEP']),('SAME_WITHOUT_NEW',scores[cid,m,sc,'WITHOUT_NEW'])]
                    admission=C.inverse_direction(target,admission_alt,key)
                    anet=C.inverse_net(target,admission_alt,key)
                    best=max((z['subtotal'],label) for label,z in aa)
                    _,nf=C.RE.fare(origin,dest,sc)
                    n=sum(f['origin_airport']==origin and f['destination_airport']==dest and f['saleable_seats']>0 and
                          f['pattern_id'].startswith('NEW-') for f in target['flights'])
                    gg=target['markets'][key]['groups']
                    q_at=None
                    if inv.get('required_potential') is not None:
                        kk=C.kernel(gg,inv['required_potential'],target['markets'][key]['outside_weight'])
                        q_at=sum(q for q,g in zip(kk['q'],gg) if g['new'] and g['a']==origin and g['b']==dest)/n if n else None
                    thresholds.append(common|dict(candidate=cid,closed_chain=t['source']['path'],cohort=t['cohort'],
                        cohort_key=t['cohort_key'],working_tails=len(t['tails'])-1,separate_R1=True,
                        representative_selection='preferred oldtop/control else fewest new jobs/legs then ID; fixed across months, no cross-cohort ranking',
                        dated_new_direction_departures=n,frequency_week_real_month=n*7/calendar.monthrange(2027,m)[1],
                        scenario_net_per_ticket=nf,required_net=nf*net['net_multiplier_equality'] if net['net_multiplier_equality'] is not None else None,
                        headroom_to_best_alternative=target['subtotal']-best[0],best_baseline_alternative=best[1],
                        new_R_minus_W=target['subtotal']-scores[cid,m,sc,'WITHOUT_NEW']['subtotal'],
                        required_new_q_per_departure_at_OD_equality=q_at,capacity_each_departure=100,
                        same_K_W_OD_status=admission['status'],same_K_W_required_potential=admission.get('required_potential'),
                        same_K_W_required_scale=admission.get('required_scale'),same_K_W_net_status=anet['net_status'],
                        same_K_W_required_net=nf*anet['net_multiplier_equality'] if anet['net_multiplier_equality'] is not None else None,
                        alternatives=len(aa),**inv,**net))
    table('pair_results.csv',pairs);table('pair_month_thresholds.csv',thresholds)
    return thresholds

def annual_outputs(E,scores,menus):
    annual=[];season=[];versus=[];plans={};stitch_receipts={}
    for key,menu in menus.items():
        t=C.templates()[menu[0]['candidate']]
        # Every fixed programme, including old-only counterfactuals, is checked
        # as a complete annual sequence before an annual scalar is accepted.
        checks={}
        for item in menu:
            label=item['candidate']+'/'+item['state']
            # A fixed ISO template has the identical infinite recurrence in
            # every month. The adapter checks all surrounding repetitions and
            # carries for all12 months; their UTC departure partitions are an
            # exact full-job year union. Full annual event lists are materialised
            # for changed monthly policies and finalists only.
            for m in range(1,13):E.calendar(item['jobs'],item['tails'],m)
            check=dict(conflicts=[],status='PERIODIC_FIXED_TEMPLATE_ALL12_PADDED_SEAMS_PASS')
            checks[label]=check
            for sc in CONFIG['scenarios']:
                zs=[E.score(item['jobs'],item['tails'],m,sc) for m in range(1,13)]
                annual.append(dict(cohort=t['cohort'],cohort_key=key,candidate=item['candidate'],state=item['state'],scenario=sc,
                    working_tails=len(item['tails'])-1,separate_R1=True,
                    known_annual_subtotal=sum(z['subtotal'] for z in zs) if not check['conflicts'] else None,
                    net_revenue=sum(z['net_revenue'] for z in zs),variable_cost=sum(z['variable_cost'] for z in zs),
                    journeys=sum(z['journeys'] for z in zs),departures=sum(z['departures'] for z in zs),
                    stitch_status=check['status'],stitch_conflicts=len(check['conflicts']),
                    return_state='PERIODIC_FIXTURE_CHECKED; actual outside operations UNKNOWN',
                    F_station_minimum_seasonal_setup_C_D_R1=None,full_profit=None,cash=None))
        for sc in CONFIG['scenarios']:
            totals={item['candidate']+'/'+item['state']:sum(E.score(item['jobs'],item['tails'],m,sc)['subtotal'] for m in range(1,13))
                for item in menu if not checks[item['candidate']+'/'+item['state']]['conflicts']}
            winner=max(totals,key=lambda x:(totals[x],x));fixed=next(i for i in menu if i['candidate']+'/'+i['state']==winner)
            monthly={}
            for m in range(1,13):
                item=max(menu,key=lambda i:(E.score(i['jobs'],i['tails'],m,sc)['subtotal'],i['candidate']+'/'+i['state']))
                monthly[m]=item
            policy={m:i['jobs'] for m,i in monthly.items()}
            stitched=C.annual_calendar(policy,t['tails'])
            upper=sum(E.score(i['jobs'],i['tails'],m,sc)['subtotal'] for m,i in monthly.items())
            requested_conflicts=stitched['conflicts']
            if requested_conflicts:
                # Select a concrete feasible alternative, preserving the rejected
                # independent optimum only as a separately labelled bound.
                monthly={m:fixed for m in range(1,13)}
                policy={m:fixed['jobs'] for m in range(1,13)}
                stitched=C.annual_calendar(policy,t['tails'])
                assert not stitched['conflicts'],'fixed periodic fallback must pass'
            # Full jobs stay assigned to the selection at first departure. That
            # can change adjacent-month flights, frequencies and revenue.
            actual=[C.score_calendar(stitched['calendars'][m],t['tails'],2027,m,sc) for m in range(1,13)] if not stitched['conflicts'] else None
            stitched_sum=sum(z['subtotal'] for z in actual) if actual else None
            plans[key,sc]=dict(fixed=fixed,monthly=monthly,stitch=stitched,actual=actual)
            stitch_receipts[key+'/'+sc]=dict(status=stitched['status'],conflicts=stitched['conflicts'][:8],
                conflict_count=len(stitched['conflicts']),carry=stitched['carry'],whole_jobs=True,
                rejected_independent_policy_conflicts=requested_conflicts[:8],fixed_fallback=bool(requested_conflicts),
                monthly_unstitched_sum=upper,stitched_known_subtotal=stitched_sum,
                actual_entry_return_outside_ops=None)
            versus.append(dict(cohort=t['cohort'],cohort_key=key,scenario=sc,working_tails=len(t['tails'])-1,
                best_fixed_yearround=winner,fixed_annual_known_subtotal=totals[winner],
                independent_monthly_sum_UPPER_BOUND=upper,independent_monthly_minus_fixed=upper-totals[winner],
                seasonal_stitch_status=stitched['status'],conflicts=len(stitched['conflicts']),
                rejected_independent_policy_conflicts=len(requested_conflicts),fixed_fallback=bool(requested_conflicts),
                stitched_seasonal_known_subtotal=stitched_sum,
                stitched_seasonal_minus_fixed=stitched_sum-totals[winner] if stitched_sum is not None else None,
                dispatchable_annual_profit=None,seasonal_setup_station_minimum_F=None,
                disposition='conditional stitched policy' if actual else 'independent optimum remains upper bound; fixed feasible fallback '+winner))
            for m,i in monthly.items():
                z=actual[m-1] if actual else E.score(i['jobs'],i['tails'],m,sc)
                selected_template=C.templates().get(i['candidate'].removeprefix('IDLE_T3:'))
                odgate=dict(status='OLD_ONLY_MONTH_NO_NEW_FLIGHTS',required_scale=None,target_markets=[])
                if selected_template and i['state']=='REPLACE':
                    zz=E.score(i['jobs'],i['tails'],m,sc)
                    keys={(C.RE.city(f['origin']),C.RE.city(f['destination'])) for j in C.new(i['jobs']) for f in j['flights'] if f['kind']=='SERVICE'}
                    oldstates=selected_template['states']
                    odgate=C.inverse_poolset(zz,[(s,E.score(oldstates[s],i['tails'],m,sc)) for s in ('KEEP','WITHOUT_NEW')],keys)
                freq=Counter((f['origin_airport'],f['destination_airport']) for f in z['flights'] if f['saleable_seats']>0)
                for (a,b),n in sorted(freq.items()):
                    season.append(dict(cohort=t['cohort'],cohort_key=key,scenario=sc,month=f'2027-{m:02}',
                        season=C.M.exposure(2027,m)['seasons'],selected=i['candidate']+'/'+i['state'],
                        origin=a,destination=b,dated_departures=n,frequency_week=n*7/calendar.monthrange(2027,m)[1],
                        status=stitched['status'],actual_months_recomputed=bool(actual),
                        independent_bound_only=not bool(actual),fixed_yearround=winner,setup_F=None,
                        OD_switch_status=odgate['status'],OD_target_market_set=odgate['target_markets'],
                        required_monthly_OD_scale_vs_same_K_W=odgate['required_scale'],
                        other_OD_fixed=True,OD_gate_basis='finite same K/W; independent target programme exposure if stitch conflicts; not all-OD inflation'))
    # Candidate 60 x 2 annual three-state deltas remain independently visible.
    for cid,t in C.templates().items():
        for sc in CONFIG['scenarios']:
            v={s:sum(scores[cid,m,sc,s]['subtotal'] for m in range(1,13)) for s in C.STATES}
            annual.append(dict(cohort=t['cohort'],cohort_key=t['cohort_key'],candidate=cid,state='THREE_STATE_DELTA',scenario=sc,
                working_tails=len(t['tails'])-1,separate_R1=True,W_minus_K=v['WITHOUT_NEW']-v['KEEP'],
                R_minus_W=v['REPLACE']-v['WITHOUT_NEW'],R_minus_K=v['REPLACE']-v['KEEP'],
                C_common_R_minus_W=True,full_profit=None,cash=None))
    table('annual_results.csv',annual);table('seasonal_plan.csv',season);table('season_vs_yearround.csv',versus)
    return plans,stitch_receipts

def resource_outputs(E):
    master=C.M.cohort(2)['jobs'];master_ids={j['id'] for j in master}
    choices={}
    # Motivated old programme subsets: preserve route families, plus actual T1
    # and T2 subsets. This bounded menu is shared unchanged for k=1,2,3.
    route=lambda j:next(f['destination'] for f in j['flights'] if f['origin']=='SVX')
    families=sorted({route(j) for j in master})
    choices['MASTER_KEEP']=master
    for mask in range(1<<len(families)):
        use={f for idx,f in enumerate(families) if mask>>idx&1}
        choices['OLD_FAMILIES_'+'_'.join(sorted(use)) if use else 'REMOVE_ALL']= [j for j in master if route(j) in use]
    choices['OLD_T1_11']=C.M.cohort(1)['jobs'];choices['OLD_T2_4']=[j for j in master if j['tail']=='T2']
    for cid,t in C.templates().items():
        if t['cohort'] in ('K1','K2','K3'):
            for s in ('WITHOUT_NEW','REPLACE'):choices[cid+'/'+s]=t['states'][s]
    feasible={};actions=[];allocations=[]
    for k in (1,2,3):
        tails=C.M.resources({f'T{i}':'SVX' for i in range(1,k+1)})
        feasible[k]={};seen=set()
        if k>1:
            for name,v in feasible[k-1].items():
                nm='IDLE_T'+str(k)+':'+name
                feasible[k][nm]=dict(v,tails=tails)
                seen.add(C.digest(C.semantic_jobs(v['jobs'])))
                allocations.append(dict(working_budget=k,choice=nm,status='EMBEDDED_LOWER_WITH_EXTRA_TAIL_IDLE',
                    master_old_count=15,removed_old_ids=v['removed'],reserve='one separate R1',
                    used_working_tails=sorted({j['tail'] for j in v['jobs']}),background_flying_tails=0,
                    global_gap=None,global_optimum=False))
        for name,jobs in choices.items():
            jj=C.recolor_closed(jobs,k)
            if jj is None:
                allocations.append(dict(working_budget=k,choice=name,status='NOT_IN_BOUNDED_FEASIBLE_ALLOCATION',
                    reason='exact source clocks cannot be assigned by first-fit at turn60; no hidden background tail',
                    master_old_count=15,master_KEEP_1_feasible=False if name=='MASTER_KEEP' and k==1 else None))
                continue
            try:
                for m in (1,2,7,12):E.calendar(jj,tails,m)
            except ValueError as exc:
                allocations.append(dict(working_budget=k,choice=name,status='CONTINUOUS_CALENDAR_REJECTED',reason=str(exc),master_old_count=15));continue
            sem=C.digest(C.semantic_jobs(jj))
            if sem in seen:continue
            seen.add(sem)
            removed=sorted(master_ids-{j['id'] for j in C.old(jj)})
            feasible[k][name]=dict(jobs=jj,tails=tails,removed=removed)
            allocations.append(dict(working_budget=k,choice=name,status='FINITE_MENU_FEASIBLE_TURN60_NOT_DISPATCH',
                master_old_count=15,retained_old_count=15-len(removed),removed_old_ids=removed,
                removal_C='sum C_i for disclosed removed old IDs; UNKNOWN',reserve='one separate R1',
                used_working_tails=sorted({j['tail'] for j in jj}),background_flying_tails=0,
                global_gap=None,global_optimum=False))
    rows=[];selected={}
    for sc in CONFIG['scenarios']:
        for m in range(1,13):
            prev=None
            for k in (1,2,3):
                vals={name:E.score(v['jobs'],v['tails'],m,sc) for name,v in feasible[k].items()}
                name=max(vals,key=lambda x:(vals[x]['subtotal'],x));z=vals[name];v=feasible[k][name]
                selected[k,m,sc]=dict(name=name,score=z,allocation=v)
                delta=z['subtotal']-prev['score']['subtotal'] if prev else None
                rows.append(dict(record_type='FINITE_MENU_FRONTIER',month=f'2027-{m:02}',scenario=sc,working_budget=k,master_old_obligations=15,
                    master_universe='B2_ALL15_IDENTICAL_FOR_EVERY_K',world_hash=C.WORLD_HASH(),separate_R1=True,
                    choice=name,finite_menu_V_before_unknown_C_D_F=z['subtotal'],net_revenue=z['net_revenue'],variable_cost=z['variable_cost'],
                    previous_choice=prev['name'] if prev else None,paired_delta_before_C_D_lease_R1=delta,
                    exact_within_declared_menu=True,global_optimum=False,global_gap=None,
                    delta_interpretation='conditional payment ceiling for THIS paired allocation at C=0 lower-bound scenario; no global next-tail value',
                    removed_old_ids=v['removed'],previous_removed_old_ids=prev['allocation']['removed'] if prev else None,
                    cancellation_adjustment='C(previous removed)-C(current removed); actual UNKNOWN',
                    outside_D_new_lease_R1_burden=None,full_marginal_profit=None,
                    additional_payments_strictly_less_than=delta,background_flying_tails=0,
                    master_KEEP_1_status='INFEASIBLE_EXACT_SOURCE_CLOCKS; not substituted as primary K1 KEEP' if k==1 else 'not one-tail master KEEP',
                    unsearched='weekly mixed paths/other retimings/partial route family choices; global gap UNKNOWN'))
                prev=selected[k,m,sc]
    for sc in CONFIG['scenarios']:
        previous_annual=None
        for k in (1,2,3):
            tails=C.M.resources({f'T{i}':'SVX' for i in range(1,k+1)})
            fixedname=max(feasible[k],key=lambda name:(sum(E.score(feasible[k][name]['jobs'],tails,m,sc)['subtotal'] for m in range(1,13)),name))
            candidates=[('BEST_FIXED:'+fixedname,{m:feasible[k][fixedname]['jobs'] for m in range(1,13)}),
                ('MONTHLY_FRONTIER',{m:selected[k,m,sc]['allocation']['jobs'] for m in range(1,13)})]
            if previous_annual:candidates.append(('LOWER_POLICY_EXTRA_TAIL_IDLE',previous_annual['policy']))
            accepted=[];rejected=[]
            for label,policy in candidates:
                stitch=C.annual_calendar(policy,tails)
                if stitch['conflicts']:
                    rejected.append(dict(policy=label,conflicts=len(stitch['conflicts'])));continue
                zs=[C.score_calendar(stitch['calendars'][m],tails,2027,m,sc) for m in range(1,13)]
                accepted.append(dict(name=label,policy=policy,subtotal=sum(z['subtotal'] for z in zs),stitch=stitch,
                    net_revenue=sum(z['net_revenue'] for z in zs),variable_cost=sum(z['variable_cost'] for z in zs)))
            winner=max(accepted,key=lambda v:(v['subtotal'],v['name']))
            delta=winner['subtotal']-previous_annual['subtotal'] if previous_annual else None
            rows.append(dict(record_type='ANNUAL_STITCHED_FINITE_FRONTIER',month='2027_YEAR',scenario=sc,working_budget=k,
                master_old_obligations=15,master_universe='B2_ALL15_IDENTICAL_FOR_EVERY_K',world_hash=C.WORLD_HASH(),separate_R1=True,
                choice=winner['name'],finite_menu_V_before_unknown_C_D_F=winner['subtotal'],net_revenue=winner['net_revenue'],variable_cost=winner['variable_cost'],
                previous_choice=previous_annual['name'] if previous_annual else None,paired_delta_before_C_D_lease_R1=delta,
                stitch_status=winner['stitch']['status'],rejected_policy_seams=rejected,
                exact_within_declared_menu=True,global_optimum=False,global_gap=None,background_flying_tails=0,
                cancellation_adjustment='sum monthly C(previous removed)-C(current removed); actual UNKNOWN',
                delta_interpretation='annual full-job stitched finite-policy payment ceiling; no global optimality or actual zero C/D/F',
                additional_payments_strictly_less_than=delta,full_marginal_profit=None))
            selected['annual',k,sc]=winner;previous_annual=winner
    # Source-supplied eight exact nested pairs remain visible independently of
    # which allocation wins this broader bounded frontier.
    spec=C.programme_input()
    if spec:
        byid={p['id']:p for p in spec['programmes']}
        for pair in spec['nested_allocations']['pairs']:
            lo=next(v for v in byid[pair['lower_programme']]['variants'] if v['cohort']=='K2')
            hi=pair['upper_variant'];ls=C.restore_variant(lo,spec);hs=C.restore_variant(hi,spec)
            lt=C.M.resources(lo['initial_positions']);ht=C.M.resources(hi['initial_positions'])
            for m in range(1,13):
                for sc in CONFIG['scenarios']:
                    l=E.score(ls['REPLACE'],lt,m,sc);h=E.score(hs['REPLACE'],ht,m,sc)
                    rows.append(dict(record_type='PROVIDED_EXACT_NESTED_PAIR',pair_id=pair['id'],month=f'2027-{m:02}',scenario=sc,
                        working_budget=3,previous_budget=2,master_old_obligations=15,world_hash=C.WORLD_HASH(),separate_R1=True,
                        lower_choice=pair['lower_programme'],upper_choice='programme_specs.nested_allocations/'+pair['id'],
                        lower_known_subtotal=l['subtotal'],upper_known_subtotal=h['subtotal'],paired_delta_before_C_D_lease_R1=h['subtotal']-l['subtotal'],
                        cancellation_adjustment='COMMON_SAME_OLD_ACTION_MAP',actual_C_D_F_R1_difference=None,
                        global_optimum=False,global_gap=None,background_flying_tails=0,
                        delta_interpretation='provided exact feasible allocation pair, not independent primary cohort subtraction'))
    table('resource_marginal.csv',rows);table('resource_allocations.csv',allocations)
    return selected

def opportunity_graph(selected):
    # Standalone deterministic SVG, deliberately no browser/panel side effects.
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1160" height="570" viewBox="0 0 1160 570">',
        '<rect width="1160" height="570" fill="#f8fafc"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#172033}.small{font-size:12px}.axis{stroke:#94a3b8;stroke-width:1}</style>',
        '<text x="36" y="36" font-size="23">Next-tail opportunity: same master 15 old obligations</text>',
        '<text x="36" y="59" class="small">Annual stitched finite policies. Extra burden = D + new lease + incremental R1 + setup + differential C.</text>']
    colors=['#2563eb','#d97706']
    for pane,sc in enumerate(CONFIG['scenarios']):
        ds=[(selected['annual',k+1,sc]['subtotal']-selected['annual',k,sc]['subtotal'])/1e6 for k in (1,2)]
        xmax=max(1,max(ds)*1.3);ymax=max(1,max(ds)*1.1);ymin=-xmax
        left=75+pane*565;top=115;width=460;height=310
        px=lambda x:left+width*x/xmax
        py=lambda y:top+height*(ymax-y)/(ymax-ymin)
        parts.append(f'<text x="{left}" y="95" font-size="18">{sc.upper()}</text>')
        parts.append(f'<path d="M{left},{top} V{top+height} H{left+width}" fill="none" class="axis"/>')
        parts.append(f'<line x1="{left}" x2="{left+width}" y1="{py(0):.2f}" y2="{py(0):.2f}" stroke="#64748b" stroke-dasharray="4 4"/>')
        for idx,d in enumerate(ds):
            color=colors[idx]
            parts.append(f'<line x1="{px(0):.2f}" y1="{py(d):.2f}" x2="{px(xmax):.2f}" y2="{py(d-xmax):.2f}" stroke="{color}" stroke-width="3"/>')
            parts.append(f'<text x="{left+12}" y="{top+22+idx*23}" class="small" style="fill:{color}">{idx+1} to {idx+2} working: ceiling {d:.3f} mln RUB/year</text>')
        for n in range(5):
            x=xmax*n/4
            parts.append(f'<text x="{px(x):.2f}" y="{top+height+20}" text-anchor="middle" class="small">{x:.1f}</text>')
            y=ymin+(ymax-ymin)*n/4
            parts.append(f'<text x="{left-8}" y="{py(y)+4:.2f}" text-anchor="end" class="small">{y:.1f}</text>')
        parts.append(f'<text x="{left}" y="{top+height+45}" class="small">Added annual burden (mln RUB)</text>')
        parts.append(f'<text x="{left}" y="{top+height+65}" class="small">Y: remaining contribution after burden (mln RUB)</text>')
    parts.extend(['<text x="36" y="525" class="small">Conditional model ceiling only; C, external own loss, released fleet, actual invoices and SJ/PD8 economics remain UNKNOWN.</text>',
        '<text x="36" y="547" class="small">Global gap UNKNOWN. Primary K1(11 jobs) vs K2(15 jobs) totals are never subtracted as next-tail value.</text>','</svg>'])
    (HERE/'opportunity_curve.svg').write_text('\n'.join(parts)+'\n')

def delivery_outputs(selected):
    resource=C.js(C.P38/'contract/resource_contract.json');rows=[];roadmap=[]
    prefix_cache={}
    def dated_prefix(arrivals,sc):
        key=C.digest(arrivals)+sc
        if key in prefix_cache:return prefix_cache[key]
        tails=C.M.resources({f'T{i}':'SVX' for i in range(1,len(arrivals)+2)})
        for idx,e in enumerate(arrivals):
            tt=next(t for t in tails if t['id']=='T'+str(idx+2))
            tt['available_from']=e['entry']+'T00:00:00Z';tt['available_to']='2029-02-01T00:00:00Z'
        policy={m:selected['annual',1+sum(e['entry']<=f'2027-{m:02}-01' for e in arrivals),sc]['policy'][m] for m in range(1,13)}
        final_budget=1+sum(e['entry']<'2028-01-01' for e in arrivals)
        stitch=C.annual_calendar(policy,tails,pre_policy=selected['annual',1,sc]['policy'][12],
            post_policy=selected['annual',final_budget,sc]['policy'][1])
        conflicts=len(stitch['conflicts']);fallback=False
        if conflicts:
            policy=selected['annual',1,sc]['policy'];fallback=True
            stitch=C.annual_calendar(policy,tails,pre_policy=policy[12],post_policy=policy[1])
            assert not stitch['conflicts'],'even idle delivered-tail fallback failed'
        vals=[C.score_calendar(stitch['calendars'][m],tails,2027,m,sc) for m in range(1,13)]
        result=dict(subtotal=sum(z['subtotal'] for z in vals),departures=sum(z['departures'] for z in vals),
            new_departures=sum(z['new_departures'] for z in vals),conflicts=conflicts,fallback=fallback,
            status='FEASIBLE_BASE1_POLICY_EXTRA_TAILS_IDLE' if fallback else 'DATED_ENTRY_WHOLE_JOB_STITCH_PASS',
            before_entry_flights=sum(1 for m in range(1,13) for f in stitch['calendars'][m]['flights']
                if C.M.dt(f['departure_utc'])<C.M.dt(next(t for t in tails if t['id']==f['tail'])['available_from'])))
        assert result['before_entry_flights']==0
        prefix_cache[key]=result;return result
    for case,arrivals in resource['deliveries'].items():
        if not arrivals:
            rows.append(dict(case=case,tail='NONE',entry=None,new_SJ_2027=0,actual_SJ_margin=None,
                resource_envelope='released existing RRJ only; R1 separate',forecast=False))
        for idx,entry in enumerate(arrivals):
            date=entry['entry'];months=[m for m in range(1,13) if f'2027-{m:02}-01'>=date]
            for sc in CONFIG['scenarios']:
                low,high=idx+1,idx+2
                before=dated_prefix(arrivals[:idx],sc);after=dated_prefix(arrivals[:idx+1],sc)
                ds=[selected[high,m,sc]['score']['subtotal']-selected[low,m,sc]['score']['subtotal'] for m in months]
                costs=[];BH=[]
                for m in months:
                    zz=selected[high,m,sc]['score'];newtail=[f for f in zz['flights'] if f['tail_id']=='T'+str(high)]
                    costs.append(sum(C.variable(f['origin_airport'],f['destination_airport'],f['block_hours_costscreen']*60,sc)['fixed_cost'] for f in newtail))
                    BH.append(sum(f['block_hours_costscreen'] for f in newtail))
                cost_limit=sum(ds)+sum(costs)
                rows.append(dict(case=case,tail=entry['id'],delivery=entry['delivery'],entry=date,scenario=sc,
                    actual_SJ_margin=None,actual_SJ_variable_cost=None,actual_PD8_cost_BH=None,
                    RRJ_resource_equivalent_2027_envelope=sum(ds),available_2027_months=months,
                    working_budget_before=low,working_budget_after=high,paired_master_old=15,
                    SJ_total_variable_plus_fixed_D_R1_cost_ceiling=cost_limit if months else None,
                    assigned_new_tail_BH=sum(BH),
                    SJ_variable_RUB_per_BH_ceiling_before_lease_D_R1=cost_limit/sum(BH) if sum(BH)>0 else None,
                    cost_threshold='Hold other allocated tails at RRJ analogue costs; SJ assigned highest-budget tail total variable + incremental lease/R1/D/activation < proxy_delta + replaced_RRJ_variable_cost; all C differences still apply',
                    new_total_payments_ceiling_proxy=sum(ds),forecast=False,guaranteed_delivery=False,
                    dated_entry_calendar_status=after['status'],candidate_entry_seam_conflicts=after['conflicts'],
                    feasible_fallback_extra_tails_idle=after['fallback'],
                    dated_entry_stitched_RRJ_proxy_increment=after['subtotal']-before['subtotal'],
                    dated_entry_incremental_departures=after['departures']-before['departures'],
                    dated_entry_incremental_new_departures=after['new_departures']-before['new_departures'],
                    before_entry_flights=after['before_entry_flights'],actual_release_certification_crew_MRO=None,
                    annual_delay_effect='actual available months recalculated; 2028 economics not extrapolated from 2027'))
            roadmap.append(dict(case=case,tail=entry['id'],delivery=entry['delivery'],entry=date,
                time_gate='H2_2027_AND_entry_AND_actual_acceptance; S1D6 2028 only',
                contribution='same-master RRJ resource-equivalent envelope, not PD8 margin',
                gates='certification; actual delivery/acceptance; crew; MRO; dispatch; OD/net; lease; separate R1; D',
                scale='frequency/tail only when incremental joint contribution after all costs > best same-cohort alternative',
                accepted_strategy=False))
    roadmap.extend([dict(case='2027_EXISTING',time_gate='all months before and after H2 conditional released RRJ only',
        gates='actual fleet-release + R1 + old obligation opportunity + slots/FDP/payload',accepted_strategy=False),
        dict(case='2028_CONDITIONAL',time_gate='S1D6 Feb/May only after entry',
        gates='rerun actual 2028 calendar, OD, type costs and available months; do not promise 2027 envelope',accepted_strategy=False)])
    table('delivery_cases.csv',rows);table('roadmap_2027_2028.csv',roadmap)

def select_finalists(scores):
    # Three distinct route/mixed programmes on identical K2 obligations/resources.
    vals=[]
    for cid,t in C.templates().items():
        if t['cohort']=='K2':
            delta=sum(scores[cid,m,'base','REPLACE']['subtotal']-scores[cid,m,'base','WITHOUT_NEW']['subtotal'] for m in range(1,13))
            if delta>0:
                total=sum(scores[cid,m,'base','REPLACE']['subtotal'] for m in range(1,13))
                vals.append((total,cid,t['source']['path']))
    chosen=[];paths=set()
    for value,cid,path in sorted(vals,reverse=True):
        if path not in paths:chosen.append(cid);paths.add(path)
        if len(chosen)==3:break
    return chosen

def finalist_outputs(E,finals,scores):
    weekly=[];ledger=[];gates=[];delays=[];details=[]
    for cid in finals:
        t=C.templates()[cid];jobs=t['states']['REPLACE'];tails=t['tails']
        st=C.annual_calendar({m:jobs for m in range(1,13)},tails)
        for season,m in [('winter',2),('spring',4),('summer',7),('autumn',10)]:
            z=scores[cid,m,'base','REPLACE'];cal=z['cal']
            for j in jobs:
                for f in j['flights']:
                    stamp=C.M.REFERENCE+timedelta(minutes=f['dep'])
                    arr=C.M.REFERENCE+timedelta(minutes=f['arr'])
                    weekly.append(dict(candidate=cid,cohort='K2',selection='DISTINCT_PATH_FINITE_MENU_RESEARCH_FINALIST_NOT_LAUNCH',season=season,
                        tail=f['tail'],old_job_id=None if j['id'].startswith('NEW-') else j['id'],job_id=j['id'],flight_id=f['flight_id'],
                        origin=f['origin'],destination=f['destination'],kind=f['kind'],iso_weekday_UTC=stamp.isoweekday(),
                        departure_UTC=stamp.strftime('%H:%M'),arrival_UTC=arr.strftime('%H:%M'),arrival_day_offset=(arr.date()-stamp.date()).days,
                        departure_local=stamp.astimezone(C.M.ZoneInfo(C.M.ZONES[f['origin']])).strftime('%a %H:%M %z'),
                        block_minutes=f['block'],service_seats=0 if f['kind']=='PAID_FERRY' else 100,
                        working_tails=2,separate_reserve='R1_NOT_ASSIGNED',actual_dispatch=None,seasonal_pattern='fixed selected weekly template; no seasonal route forecast'))
            # A representative actual ISO week only, no all-candidate ledgers.
            start=datetime(2027,m,8,tzinfo=C.UTC);start-=timedelta(days=start.weekday());end=start+timedelta(days=7)
            for f in cal['flights']:
                if not start<=C.M.dt(f['departure_utc'])<end:continue
                key=(C.RE.city(f['origin']),C.RE.city(f['destination']));mm=z['markets'][key]
                for sc in CONFIG['scenarios']:
                    zz=scores[cid,m,sc,'REPLACE'];market=zz['markets'][key]
                    q=next((q/g['n'] for q,g in zip(market['q'],market['groups']) if f['flight_id'] in g['flight_ids']),0.)
                    cost=C.variable(f['origin'],f['destination'],f['block_minutes'],sc)
                    net=C.RE.fare(f['origin'],f['destination'],sc)[1] if f['kind']=='service' else 0
                    ledger.append(dict(candidate=cid,season=season,scenario=sc,flight_id=f['flight_id'],old_id=f['rotation_id'] if not f['rotation_id'].startswith('NEW-') else None,
                        tail=f['tail'],origin=f['origin'],destination=f['destination'],departure_utc=f['departure_utc'],arrival_utc=f['arrival_utc'],
                        kind=f['kind'],seats=100 if f['kind']=='service' else 0,direct_q=q,through_q=0,net_per_journey=net,revenue=q*net,
                        fuel_t=cost['fuel_t'],landed_RUB_per_t=cost['fuel_price'],fuel_cost=cost['fuel_cost'],
                        other_variable=cost['other_cost'],variable_cost=cost['fixed_cost'],fixed_crew_excluded=cost['fixed_crew_excluded'],
                        deice_allowance_not_fact=cost['deice_allowance'],unknown_cost_F=None,actual_profit=None))
        for turn in (60,90):
            try:
                for m in (1,2,4,7,10,12):E.calendar(jobs,tails,m,turn)
                status='CONTINUOUS_POSITION_TURN_PASS_NOT_DISPATCH';reason=None
            except ValueError as exc:status='CONTINUOUS_TURN_FAIL';reason=str(exc)
            gates.append(dict(candidate=cid,gate='CONTINUOUS_TURN_'+str(turn),status=status,reason=reason,
                actual_crew_FDP=None,slots=None,MRO=None,tail_release=None,payload=None,BH8='diagnostic only; 20:00 is not legal reset'))
        events=sorted(st['events'],key=lambda f:f['departure_utc'])
        # Delay every new AND retained departure in four representative actual
        # weeks. Propagate into the following 14 days without day/week reset.
        for season,m in [('winter',2),('spring',4),('summer',7),('autumn',10)]:
            start=datetime(2027,m,8,tzinfo=C.UTC);start-=timedelta(days=start.weekday());end=start+timedelta(days=7)
            monthend=C.M.bounds(2027,m)[1]
            for hold in (30,60,120):
                for targetkind in ('new','retained'):
                    observations=[]
                    for tid in ('T1','T2'):
                        seq=[f for f in events if f['tail']==tid]
                        for idx,f in enumerate(seq):
                            trigger_dep=C.M.dt(f['departure_utc'])
                            in_window=start<=trigger_dep<end or monthend-timedelta(days=2)<=trigger_dep<monthend or (
                                season=='winter' and datetime(2027,12,30,tzinfo=C.UTC)<=trigger_dep<datetime(2028,1,1,tzinfo=C.UTC))
                            if not in_window:continue
                            isnew=f['rotation_id'].startswith('NEW-')
                            if isnew!=(targetkind=='new'):continue
                            ready=None;affected=[];maxdelay=0;crossmonth=False;crossweek=False;absorbed=False;oldids=set();shortfall=0
                            for ii,g in enumerate(seq[idx:]):
                                scheduled=C.M.dt(g['departure_utc']);arr=C.M.dt(g['arrival_utc'])
                                if scheduled>trigger_dep+timedelta(days=14):break
                                shifted=max(scheduled+(timedelta(minutes=hold) if ii==0 else timedelta()),ready or scheduled)
                                delay=(shifted-scheduled).total_seconds()/60
                                if ii and delay<=1e-9:absorbed=True;break
                                ready=shifted+(arr-scheduled)+timedelta(minutes=60)
                                maxdelay=max(maxdelay,delay);crossmonth|=shifted.month!=scheduled.month
                                if delay>0:
                                    crossmonth|=scheduled.month!=trigger_dep.month
                                    crossweek|=scheduled.isocalendar()[:2]!=trigger_dep.isocalendar()[:2]
                                if ii and delay>0:
                                    affected.append(g['flight_id'])
                                    if not g['rotation_id'].startswith('NEW-'):oldids.add(g['rotation_id'].split('@')[0])
                                    shortfall=max(shortfall,delay)
                            observations.append(dict(candidate=cid,season=season,hold_minutes=hold,target_kind=targetkind,
                                trigger=f['flight_id'],tail=tid,propagated_flights=len(affected),affected_old_ids=sorted(oldids),
                                buffer_needed_minutes=shortfall,max_departure_delay=maxdelay,absorbed_within_context=absorbed,
                                cross_month=crossmonth,cross_week=crossweek,latest_slot_extension_required_minutes=maxdelay,
                                cancellation_trigger=None,cancellation_RUB=None,crew_limit_minutes=None,
                                required_gate='actual latest slots / continuous crew duty-rest limits / recovery plan; no invented legal cutoff'))
                    delays.append(dict(candidate=cid,season=season,hold_minutes=hold,target_kind=targetkind,triggers=len(observations),
                        max_propagated_flights=max([r['propagated_flights'] for r in observations] or [0]),
                        max_buffer_needed_minutes=max([r['buffer_needed_minutes'] for r in observations] or [0]),
                        affected_old_ids=sorted({x for r in observations for x in r['affected_old_ids']}),
                        unabsorbed=sum(not r['absorbed_within_context'] for r in observations),
                        triggers_crossing_month=sum(r['cross_month'] for r in observations),triggers_crossing_week=sum(r['cross_week'] for r in observations),
                        trigger_scope='season ISO week + month last2days + Dec30/31 winter yearwrap',
                        monetary_loss=None,slot_FDP_limits=None,continuous_calendar=True))
                    details.extend(sorted(observations,key=lambda r:(r['propagated_flights'],r['buffer_needed_minutes'],r['trigger']),reverse=True)[:2])
    table('three_finalists_weekly.csv',weekly);table('three_finalists_ledger.csv',ledger)
    table('delay_summary.csv',delays);table('delay_details.csv',details)
    return gates

def sensitivity_outputs(E,finals,scores):
    rows=[]
    for cid in finals:
        t=C.templates()[cid]
        for m in range(1,13):
            for sc in CONFIG['scenarios']:
                for incidence in (0,.25,1):
                    zz={s:E.score(j,t['tails'],m,sc,incidence=incidence) for s,j in t['states'].items()}
                    rows.append(dict(candidate=cid,month=f'2027-{m:02}',scenario=sc,case='DEICE_INCIDENCE_'+str(incidence),
                        same_world_all_states=True,KEEP=zz['KEEP']['subtotal'],WITHOUT_NEW=zz['WITHOUT_NEW']['subtotal'],REPLACE=zz['REPLACE']['subtotal'],
                        R_minus_W=zz['REPLACE']['subtotal']-zz['WITHOUT_NEW']['subtotal'],
                        interpretation='seasonal incidence stress, not an invoice or factual August winter charge'))
        for m in (1,4,7,10):
            for sc in CONFIG['scenarios']:
                cases=[('DIRECTION_35_65',dict(split=.35)),('DIRECTION_65_35',dict(split=.65)),
                    ('WEAK_NONBASE_OD_HALF',dict(weak=True)),('COMPETITOR_FARE_MINUS10_FREQ_PLUS25',dict(response='price_match10_capacity25')),
                    ('NEW_RETAIL_FARE_MINUS10_RECHOICE',dict(fare_scale=.9))]
                for label,kw in cases:
                    zz={s:E.score(j,t['tails'],m,sc,**kw) for s,j in t['states'].items()}
                    rows.append(dict(candidate=cid,month=f'2027-{m:02}',scenario=sc,case=label,same_world_all_states=True,
                        KEEP=zz['KEEP']['subtotal'],WITHOUT_NEW=zz['WITHOUT_NEW']['subtotal'],REPLACE=zz['REPLACE']['subtotal'],
                        R_minus_W=zz['REPLACE']['subtotal']-zz['WITHOUT_NEW']['subtotal'],
                        interpretation='explicit planning stress; not probability or predicted response; fare change recalculates choice'))
        for m,daycase in ((1,'JAN_PEAK'),(7,'SUMMER_PEAK')):
            for sc in CONFIG['scenarios']:
                vals={}
                for s in C.STATES:
                    z=scores[cid,m,sc,s]
                    zz=C.full_p06(z['cal'],t['tails'],m,sc,day_case=daycase)
                    vals[s]=zz['revenue']-z['variable_cost']
                rows.append(dict(candidate=cid,month=f'2027-{m:02}',scenario=sc,case='NORMALIZED_DATED_'+daycase,
                    same_world_all_states=True,KEEP=vals['KEEP'],WITHOUT_NEW=vals['WITHOUT_NEW'],REPLACE=vals['REPLACE'],R_minus_W=vals['REPLACE']-vals['WITHOUT_NEW'],
                    interpretation='scenario dates, official holiday calendar not verified; requested-date weights .5/1.5 normalize actual calendar; one monthly pool, no premium or additional annual OD'))
        # Through fully joint, fare once, both physical capacities consumed.
        # Only Jan/Jul diagnostic exposure, not a main assumed annual revenue.
        for m in (1,7):
            for sc in CONFIG['scenarios']:
                vals={}
                for s,j in t['states'].items():
                    z=scores[cid,m,sc,s]
                    zz=C.full_p06(z['cal'],t['tails'],m,sc,through=True)
                    vals[s]=zz['revenue']-z['variable_cost']
                rows.append(dict(candidate=cid,month=f'2027-{m:02}',scenario=sc,case='CONDITIONAL_TWO_LEG_THROUGH',same_world_all_states=True,
                    KEEP=vals['KEEP'],WITHOUT_NEW=vals['WITHOUT_NEW'],REPLACE=vals['REPLACE'],R_minus_W=vals['REPLACE']-vals['WITHOUT_NEW'],
                    interpretation='unconfirmed offered same-tail 60..240 minute through; fare once, seats both legs; no cross-month through added'))
    # Re-check all 238 old directed cost ceilings in every full month. Cost
    # incidence 0/25/100% tests cover an optimistic no-deice summer too.
    edges=C.read(C.P36/'pass2/structural_cautious_bounds.csv')
    for m in range(1,13):
        for incidence in (0,.25,1):
            vals=[]
            for r in edges:
                c=C.variable(r['origin'],r['destination'],float(r['block_minutes']),'cautious',incidence)
                cap=(float(r['cautious_netfare'])*100 if r['kind']=='SERVICE' else 0)-c['fixed_cost']
                vals.append(cap)
            rows.append(dict(candidate='ALL_P36_DIRECT_EDGES',month=f'2027-{m:02}',scenario='cautious',case='FULL100_DEICE_'+str(incidence),
                edges=len(vals),negative_edges=sum(v<0 for v in vals),maximum_full100_contribution=max(vals),
                interpretation='standalone direct ceiling only; not joint through/global portfolio proof; fixed crew excluded'))
    table('sensitivities.csv',rows)

def pilot_outputs(E,scores,menus,pair_thresholds):
    rows=[]
    choices=[]
    for cid,t in C.templates().items():
        if t['cohort']!='K2':continue
        ff=[f for j in C.new(t['states']['REPLACE']) for f in j['flights'] if f['kind']=='SERVICE']
        counts=Counter((f['origin'],f['destination']) for f in ff)
        if counts['GOJ','KJA'] and counts['KJA','GOJ']:
            choices.append((max(counts['GOJ','KJA'],counts['KJA','GOJ']),len(ff),cid))
    goj=min(choices)[2] if choices else 'X_GOJ_KJA_R'
    for cid in ('X_SVX_KJA','X_SVX_IKT',goj):
        t=C.templates()[cid]
        for sc in CONFIG['scenarios']:
            for stress,kw in [('MAIN',{}),('COMPETITOR_FARE_MINUS10_FREQ_PLUS25',dict(response='price_match10_capacity25')),
                ('WEAK_NONBASE_OD_HALF',dict(weak=True)),('COMBINED_35_65',dict(response='price_match10_capacity25',weak=True,split=.35,fare_scale=.9)),
                ('COMBINED_65_35',dict(response='price_match10_capacity25',weak=True,split=.65,fare_scale=.9))]:
                m=2;z=E.score(t['states']['REPLACE'],t['tails'],m,sc,**kw)
                w=E.score(t['states']['WITHOUT_NEW'],t['tails'],m,sc,**kw);k=E.score(t['states']['KEEP'],t['tails'],m,sc,**kw)
                alt=[]
                for item in menus[t['cohort_key']]:
                    q=E.score(item['jobs'],item['tails'],m,sc,**kw)
                    if q['semantic']!=z['semantic']:alt.append((q['subtotal'],item['candidate']+'/'+item['state']))
                best=max(alt)
                newfl=[f for f in z['flights'] if f['pattern_id'].startswith('NEW-') and f['saleable_seats']>0]
                freq=Counter(f['origin_airport']+'>'+f['destination_airport'] for f in newfl)
                scale=kw.get('fare_scale',1.)
                price=sum(C.RE.fare(f['origin_airport'],f['destination_airport'],sc)[1]*scale for f in newfl)
                required=best[0]+z['variable_cost']-z['retained_revenue']
                n=max(0,math.floor(required/price)+1) if price else None
                required_same=max(k['subtotal'],w['subtotal'])+z['variable_cost']-z['retained_revenue']
                n_same=max(0,math.floor(required_same/price)+1) if price else None
                directional_price=Counter()
                for f in newfl:directional_price[f['origin_airport']+'>'+f['destination_airport']]+=C.RE.fare(f['origin_airport'],f['destination_airport'],sc)[1]*scale
                directional_integer={direction:max(0,math.floor((required-100*(price-coeff))/coeff)+1) for direction,coeff in directional_price.items()}
                rows.append(dict(candidate=cid,scenario=sc,stress=stress,start='2027-02-01',end='2027-02-28',weeks=4,
                directed_new_frequencies_week={key:value/4 for key,value in freq.items()},working_tails=2,separate_R1=True,new_service_departures=len(newfl),
                closed_chain=t['source']['path'],return_product='both GOJ-KJA directions in completed mixed calendar' if cid==goj and choices else 'both directions 1/week' if cid!=goj else 'one direction only; product incomplete',
                business_minimum='KJA/IKT illustrative1RT/week; GOJ smallest completed programme serving both directions (may2/week); actual customer minimum UNKNOWN',
                KEEP=k['subtotal'],WITHOUT_NEW=w['subtotal'],REPLACE=z['subtotal'],best_alternative=best[1],best_alternative_subtotal=best[0],
                R_minus_W=z['subtotal']-w['subtotal'],R_minus_KEEP=z['subtotal']-k['subtotal'],R_minus_best=z['subtotal']-best[0],
                integer_equal_tickets_each_new_service_departure=n,seat_capacity=100,integer_bound_feasible=n<=100 if n is not None else False,
                integer_equal_tickets_vs_KEEP_same_W=n_same,
                required_common_new_net_full100_vs_KEEP_same_W=required_same/(100*len(newfl)) if newfl else None,
                directional_integer_required_if_other_new_legs_full100=directional_integer,
                directional_bound_basis='strict integer tickets per dated departure; all other new legs full100 is an optimistic capacity boundary, not sales',
                required_common_new_net_at_full100=required/(100*len(newfl)) if newfl else None,
                input_flip='actual net at feasible q must exceed threshold and fund all F/D/R1/exit; or verified variable costs below retained-adjusted revenue minus best alternative; not an assumed tariff increase',
                BEP_basis='strict >0 vs best finite menu; retained sales fixed at baseline: ticket diagnostic, not a new OD forecast',
                modelled_new_to_RW=max(0,z['journeys']-w['journeys']),internal_diverted=max(0,w['retained_journeys']-z['retained_journeys']),
                external_own_diverted=None,new_leg_journeys=z['new_journeys'],
                conditional_opportunity_funding_gap_before_C_D_F=max(0,best[0]-z['subtotal']),
                funding_basis='conditional zero-deduction opportunity/accrual gap, not actual funding; unknown differential comparator C can change ranking; complete cash budget requires dated payments and exit',
                required_cash_budget=None,approved_test_loss_budget=None,
                required_cash_budget_formula='max(0,-min_t cumulative paid net cash of pilot incl setup/reserve/exit); actual payment schedule UNKNOWN',
                break_budget_condition='F+D+deltaC+incrementalR1+exit < R-best_alternative + explicitly approved differential test budget B; B UNKNOWN',
                combined_unknown_F_D_exit_R1_ceiling=z['subtotal']-best[0],
                stop='q/net below inverse gate; complete cash loss incl exit exceeds approved B; loss of tail/R1/slots/FDP/payload; competitive joint delta <=0',
                expansion='next frequency only if additional joint contribution > best alternative in competitive world; observed sales+invoices+ops repeat',
                presales_last_penalty_free_cancel_deadline=None,
                recommendation='NO_PILOT_RECOMMENDATION_WITHOUT_POSITIVE_ADDITIONAL_RESULT_OR_EXPLICITLY_FUNDED_USEFUL_EXPERIMENT'))
    table('pilots.csv',rows)

def gates_outputs(final_gates):
    gates=final_gates+[
        dict(gate='ACTUAL_FLEET_RELEASE',status='UNKNOWN',reason='1/2/3 working + separate R1 are conditional envelopes, unused fixture hours not availability'),
        dict(gate='OWN_CURRENT_SUPPLY',status='BOUNDED_PUBLICATION_ONLY',reason='RW TOF/GOJ positive source periods; unmodelled connecting/other old sales D not zero'),
        dict(gate='NET_AND_ENDPOINT_OD',status='UNKNOWN',reason='0 qualified fares/net updates; P05 carrier2025 analogue not route forecast'),
        dict(gate='STATION_OVERNIGHT_CREW_SETUP_R1',status='UNKNOWN_F_THRESHOLD',reason='all missing differential costs share one headroom; fixed salary/lease not avoidable'),
        dict(gate='SLOTS_FDP_MRO_GAUGE_PAYLOAD',status='UNKNOWN_TYPED_GATES',reason='BH8 not FDP; 20:00 not duty/midnight reset; no distance-only exclusion'),
        dict(gate='MIXED_WEEKLY_PROGRAMMES',status=CONFIG['programme_admission'],reason='completed420 financialclasses/436variants admitted; finite-menu evaluation is not a global network optimum'),
        dict(gate='NEWNESS_AND_8_TO_12_ROUTES',status='NOT_PROVEN',reason='23 commercial pair scenarios + 2 positioning pairs are not 8 confirmed new economically justified routes'),
        dict(gate='SJ_PD8',status='TYPE_COST_UNKNOWN',reason='RRJ resource-equivalent only; entry/certification/crew/MRO/lease gate; no profit before entry'),
        dict(gate='PUBLIC_COST_COMPONENTS',status='NO_NUMERIC_REPLACEMENT',reason='23 public SVX rates ex VAT; quantity and ground overlap not reconciled'),
        dict(gate='SEASONAL_SETUP_AND_RETURN',status='UNKNOWN',reason='periodic stitch is not actual annual return state or free station activation')]
    table('operational_gates.csv',gates)
    req=[]
    for owner,items,threshold,unit in [
        ('Commercial','directional endpoint OD by month/date; net settlement per ticket; own direct/connecting diversion','pair_month_thresholds.csv directed OD/net winning intervals; unmodelled own loss consumes common headroom','pax; RUB/net-ticket'),
        ('Fleet/OCC','released working tails 1/2/3; separate single R1; full15 old-job master obligations; external D_i','resource_marginal.csv paired delta minus C difference / new lease / R1 / D; no free background','tail-date; RUB/month'),
        ('Airport/procurement','dated ground component invoice, MTOW, ex/inc VAT, passenger/cycle quantities, overlap','replace matched cost basket only; 610/370 etc not added on top','RUB/event; RUB/t; RUB/pax'),
        ('Crew/OCC','continuous duty/rest limits, roster, added shifts, latest slots, 30/60/120 delay recovery','delay_summary.csv buffer and latest-slot extension; monetary thresholds require actual limit/cost','minutes; RUB/shift'),
        ('Finance','cancellation C per old ID, station/overnight/parking/launch F, minimum seasonal contract, payment/exit dates','F+D+external ownloss+incremental R1+deltaC < single reported headroom; C common R-W','RUB/month; RUB/oneoff'),
        ('Fleet/SJ','PD8 consumption/MRO/cycle cost and lease, certification, entry dates, actual delivery','delivery_cases.csv resource envelope; actual SJ margin NULL until own costs','RUB/BH; RUB/cycle; date'),
        ('Partner/cargo','signed directional block/seat or kg net/volume, displacement, release/deposit/payment, residual payload','thresholds.csv conditional support/block/cargo equations; MAIN=0','RUB/net kg; paid seats')]:
        req.append(dict(owner=owner,request=items,decision_threshold=threshold,unit=unit,actual=None))
    table('RW_data_request.csv',req)

def auxiliary_thresholds(finals,scores):
    rows=[]
    for cid in finals:
        for sc in CONFIG['scenarios']:
            for m in range(1,13):
                r,w,k=(scores[cid,m,sc,s] for s in ('REPLACE','WITHOUT_NEW','KEEP'))
                gap=max(0,w['subtotal']-r['subtotal'])
                for case,formula in [
                    ('F_D_R1_OWNLOSS','combined additional losses < R-W; cancellation common R-W; vs KEEP also deltaC'),
                    ('CARGO_CONTRACT','kg_required=(gap+fixedcargo)/positive_verified_net_perkg <= approved residual payload; MAIN cargo=0'),
                    ('BLOCK_SELL','guaranteed net proceeds - displaced retail - service/risks > gap; seats consume dated inventory once'),
                    ('BLOCK_BUY','max_allin_price=contracted_resale_net-service-risk-required_contribution; no inferred passenger demand'),
                    ('SUPPORT_CONTRACT','eligible incremental support after tax/credit overlap and payment lag > gap; MAIN=0'),
                    ('EXCISE_DAMPER','conditional historical 3024/eligible_t and32930/model_t only if legal+contract+no already-netted credit; not future entitlement')]:
                    rows.append(dict(candidate=cid,month=f'2027-{m:02}',scenario=sc,case=case,
                        gap_to_same_change_without=gap,headroom_R_minus_W=r['subtotal']-w['subtotal'],
                        headroom_R_minus_KEEP_before_C=r['subtotal']-k['subtotal'],formula=formula,
                        signed_contract=None,net_per_kg_or_block=None,approved_payload=None,quantity_required=None,
                        main_extra_revenue=0,actual_full_profit=None))
    table('thresholds.csv',rows)

def run():
    before=C.guard();manifest=source_manifest()
    E=C.Engine(C.digest(dict(inputs=manifest['input_digest'],code=manifest['code_digest'])))
    scores={};rows=[];errors=[];actions=[]
    print('P38: fixed world',len(C.world()),'directed city pools;',len(C.templates()),'completed variants incl all60 legacy',flush=True)
    for idx,(cid,t) in enumerate(C.templates().items(),1):
        actions.extend(action_rows(cid,t))
        for m in range(1,13):
            for sc in CONFIG['scenarios']:
                try:
                    zz={s:E.score(j,t['tails'],m,sc) for s,j in t['states'].items()}
                except ValueError as exc:
                    errors.append(dict(candidate=cid,month=m,scenario=sc,error=str(exc)));continue
                for s,z in zz.items():
                    scores[cid,m,sc,s]=z;rows.append(state_row(cid,t,m,sc,s,z,zz))
        if idx%40==0:print('completed templates',idx,'/',len(C.templates()),flush=True)
    if errors:
        dump('calculation_errors.json',errors)
        raise ValueError('some completed template calendars rejected; see calculation_errors.json')
    # Primary cohort KEEP controls are resource-consistent; they are never
    # labelled marginal next-tail values or filled with phantom old T2 flights.
    for k in (1,2,3):
        cohort=C.M.cohort(k);t=dict(cohort=f'K{k}',cohort_key='PRIMARY_K'+str(k),tails=cohort['tails'])
        for m in range(1,13):
            for sc in CONFIG['scenarios']:
                z=E.score(cohort['jobs'],cohort['tails'],m,sc)
                for s in C.STATES:rows.append(state_row('PRIMARY_K'+str(k)+'_KEEP_CONTROL',t,m,sc,s,z,{ss:z for ss in C.STATES}))
    table('programmes_monthly.csv',rows);table('old_actions.csv',actions)
    menus=C.native_menus()
    pt=pair_outputs(E,scores,menus);print('pair/month directed inverse thresholds',len(pt),flush=True)
    plans,stitches=annual_outputs(E,scores,menus);print('annual fixed/seasonal full-job stitch checked',flush=True)
    resource=resource_outputs(E);opportunity_graph(resource);delivery_outputs(resource)
    finals=select_finalists(scores);print('same-K2 distinct research finalists',','.join(finals),flush=True)
    final_gates=finalist_outputs(E,finals,scores)
    sensitivity_outputs(E,finals,scores);pilot_outputs(E,scores,menus,pt)
    auxiliary_thresholds(finals,scores);gates_outputs(final_gates)
    coverage=dict(status=CONFIG['programme_admission'],completed_programmes_gate=CONFIG['completed_programme_gate'],
        programme_templates=len(C.templates()),legacy_templates=60,financial_classes=420,calendar_variants=436,source_positive_templates=37,
        seed_physical_pairs=25,total_source_template_physical_pairs=len({r['pair'] for r in pt}),
        seed_commercial_pairs=23,seed_positioning_only_pairs=2,
        months=12,scenarios=['base','cautious'],three_state_rows=len(rows),pair_direction_month_scenario_rows=len(pt),
        fixed_world_directed_city_pools=len(C.world()),world_hash=C.WORLD_HASH(),old_actions=len(actions),
        primary_KEEP_oldjob_counts={'K1':11,'K2':15,'K3':15},working_counts=[1,2,3],reserve='ONE_SEPARATE_R1',
        same_K2_distinct_finalists=finals,native_cohort_menus={k:len(v) for k,v in menus.items()},
        economics_calls=dict(E.calls),annual_stitch=stitches,
        resource_frontier='bounded common-master old15 allocation choices; exact in disclosed menu; global gap UNKNOWN',
        unsearched=['global mixed-path combinations beyond completed generator finite menu and other frequency/clock retiming',
            'actual own connecting/3+leg background products','actual route-month endpoint OD/net/fare/invoices',
            'physical dispatch slots/FDP/MRO/payload','actual SJ/PD8 economics','2028 economic rerun',
            'cross-month through sales and annual actual return state'],
        no_launch_recommendation=True,economically_justified_8_routes_not_proven=True,
        no_corporate_strategy_or_city_rank_changes=True)
    dump('search_coverage.json',coverage)
    manifest['guard_after']=C.guard();assert before==manifest['guard_after']
    dump('input_manifest.json',manifest);dump('source_manifest.json',dict(
        canonical_manifest='input_manifest.json',input_digest=manifest['input_digest'],guard=before,
        model_sources=manifest['formula_lineage'],financial_new_updates={'OD':0,'net':0,'invoices':0},
        cost_rate_admission='0 actual replacement;23 public SVX rates remain unpriced model_value UNKNOWN'))
    outputs={p.name:C.sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.suffix in ('.csv','.json','.svg')
        and p.name not in ('run_receipt.json','validation.json','repeatability.json')}
    dump('run_receipt.json',dict(status=CONFIG['programme_admission'],deterministic_output_sha256=outputs,
        output_digest=C.digest(outputs),input_digest=manifest['input_digest'],code_digest=manifest['code_digest'],guard_before=before,
        guard_after=manifest['guard_after'],executed=True,finalists=finals,calls=dict(E.calls)))
    print('DONE',CONFIG['programme_admission'],';',len(outputs),'data files; digest',C.digest(outputs),flush=True)

if __name__=='__main__':run()
