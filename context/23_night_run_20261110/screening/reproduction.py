#!/usr/bin/env python3
"""Independent, stdlib-only arithmetic replay and predeclared sensitivity.

Run after freeze_inputs.py. Reads frozen projections only; writes under this
directory, never imports or executes colleagues' code and never uses network.
"""
import copy
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent
IN = OUT/'inputs'
MODEL = 'context/22_stage1_audit/'
TOL = 1e-12
PROXY = ['gap_pop','pax_2025','catchment_pop_2025','transfer_demand_base','wage_2024']

def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    assert all(None not in r for r in rows), path
    return rows

def load(role,path):
    p=IN/role/path
    return json.loads(p.read_text()) if p.suffix=='.json' else read_csv(p)

def write_csv(name,rows):
    rows=list(rows)
    assert rows, name
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def dump(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def fnum(v):
    return None if v in ['',None] else float(v)

def score(z,w):
    assert set(w)==set(next(iter(z.values()))) and all(math.isfinite(v) and v>=0 for v in w.values())
    total=sum(w.values());assert total>0
    return {i:sum(w[k]*v for k,v in row.items())/total for i,row in z.items()}

def legacy_z(data,ids,front=False,anchors=None):
    z={i:{} for i in ids};miss={i:{} for i in ids}
    for c in data['criteria']:
        k=c['key']
        x={i:data['values'][i][k]['v'] for i in (anchors or ids)}
        for i,v in x.items():
            if v is None and c.get('fill') is not None:x[i]=c['fill']
        observed=[v for v in x.values() if v is not None]
        low = min(observed) if observed else 0.
        high = max(observed) if observed else 0.
        if not front:
            if c.get('lo') is not None:low=c['lo']
            if c.get('hi') is not None:high=c['hi']
        for i in ids:
            v=x[i]
            if v is None:u=.5
            else:
                u=(v-low)/(high-low) if high>low else v*0
                if c['dir']=='-':u=1-u
            z[i][k]=u
            miss[i][k]=data['values'][i][k]['v'] is None
    return z,miss

def author_stage_z(data,ids):
    z={i:{} for i in ids};low=copy.deepcopy(z);high=copy.deepcopy(z)
    unknown=copy.deepcopy(z);indirect=copy.deepcopy(z)
    for i in ids:
        for c in data['criteria']:
            k=c['key'];x=data['values'][i][k]
            assert all(k2 in x for k2 in ['u','u_low','u_high','unknown','indirect'])
            z[i][k],low[i][k],high[i][k]=x['u'],x['u_low'],x['u_high']
            unknown[i][k],indirect[i][k]=int(x['unknown']),int(x['indirect'])
            assert 0<=low[i][k]<=z[i][k]<=high[i][k]<=1
    return z,low,high,unknown,indirect

def rank_rows(z,w,low=None,high=None,unknown=None,indirect=None):
    ss=score(z,w);sl=score(low or z,w);sh=score(high or z,w)
    ids=list(z)
    order=sorted(ids,key=lambda i:-ss[i])
    result=[]
    for n,i in enumerate(order,1):
        r=dict(iata=i,rank_stable=n,score=ss[i],score_low=sl[i],score_high=sh[i],
            central_rank_min=1+sum(ss[j]>ss[i]+TOL for j in ids if j!=i),
            central_rank_max=1+sum(ss[j]>=ss[i]-TOL for j in ids if j!=i),
            rank_best=1+sum(sl[j]>sh[i]+TOL for j in ids if j!=i),
            rank_worst_inclusive=1+sum(sh[j]>=sl[i]-TOL for j in ids if j!=i),
            author_rank_best=1+sum(sl[j]>sh[i] for j in ids if j!=i),
            author_rank_worst=1+sum(sh[j]>sl[i] for j in ids if j!=i))
        if unknown:
            r['unknown_weight_share']=sum(w[k]*unknown[i][k] for k in w)/sum(w.values())
            r['indirect_weight_share']=sum(w[k]*indirect[i][k] for k in w)/sum(w.values())
            r['uncertain_weight_share']=sum(w[k]*(high[i][k]>low[i][k]) for k in w)/sum(w.values())
        result.append(r)
    return result

def summary(origin,scenario,rows,status,**kwargs):
    third=rows[2]['score'];fourth=rows[3]['score'] if len(rows)>3 else None
    return dict(origin_model=origin,scenario=scenario,replay_status=status,
        universe_n=len(rows),top3=' / '.join(r['iata'] for r in rows[:3]),
        top3_boundary_group=' / '.join(r['iata'] for r in rows if abs(r['score']-third)<=TOL),
        score1=rows[0]['score'],score2=rows[1]['score'],score3=third,
        third_fourth_gap=third-fourth if fourth is not None else '',**kwargs)

def hav(a,b):
    la,lo,lb,ln=map(math.radians,(*a,*b))
    h=math.sin((lb-la)/2)**2+math.cos(la)*math.cos(lb)*math.sin((ln-lo)/2)**2
    return 12742*math.asin(min(1,math.sqrt(h)))

def legacy_replay(role,comparisons,replays,checks):
    d=load(role,'data/processed/criteria.json');ll=load(role,'data/processed/longlist.csv')
    w={c['key']:c['weight'] for c in d['criteria']}
    all_ids=[r['iata'] for r in ll]
    olddist={r['iata']:min(float(r['dist_msk_km']),float(r['dist_ekb_km'])) for r in ll}
    for threshold in [0,500]:
        ids=[i for i in all_ids if olddist[i]>=threshold]
        z,miss=legacy_z(d,ids,front=role=='front_historical')
        rows=rank_rows(z,w)
        sfx='_min500' if threshold else ''
        saved=load(role,f'data/processed/longlist_scores{sfx}.csv')
        by={r['iata']:r for r in saved}
        errors=[abs(r['score']-float(by[r['iata']]['score'])) for r in rows]
        replay_ok=max(errors)<=.0005+TOL
        if role!='front_historical':assert replay_ok,(role,threshold,max(errors))
        # Original exports round scores before sorting; no tie at current top3 boundary.
        top_equal=[r['iata'] for r in saved[:3]]==[r['iata'] for r in rows[:3]]
        if role!='front_historical':assert top_equal
        if not replay_ok:
            write_csv(f'{role}_min{threshold}_mismatch.csv',[
                dict(iata=r['iata'],recalculated=r['score'],saved_score=by[r['iata']]['score'],
                    delta=r['score']-float(by[r['iata']]['score']),saved_rank=by[r['iata']]['rank'],replayed_rank=r['rank_stable']) for r in rows])
            normal_errors=[]
            for i in ids:
                for k in w:
                    if k in by[i] and by[i][k]!='' and abs(z[i][k]-float(by[i][k]))>.0005+TOL:
                        normal_errors.append(dict(iata=i,criterion=k,replayed=z[i][k],saved=by[i][k],delta=z[i][k]-float(by[i][k])))
            if normal_errors:write_csv(f'{role}_min{threshold}_normalization_mismatch.csv',normal_errors)
        if role=='nastya':
            lo={i:{k:0. if miss[i][k] else u for k,u in row.items()} for i,row in z.items()}
            hi={i:{k:1. if miss[i][k] else u for k,u in row.items()} for i,row in z.items()}
            rows=rank_rows(z,w,lo,hi,miss,{i:{k:0 for k in w} for i in ids})
            for r in rows:
                assert abs(round(r['score_low'],3)-float(by[r['iata']]['score_low']))<TOL
                assert abs(round(r['score_high'],3)-float(by[r['iata']]['score_high']))<TOL
        comparisons.append(summary(role,f'author_min{threshold}',rows,'PASS_ARITHMETIC_ROUNDED_EXPORT' if replay_ok else 'MISMATCH_HISTORICAL_DERIVED',
            threshold_km=threshold,bases='author_rounded_SVO_DME_VKO_SVX',mode='author_scope',profile='author_weights',
            weight_sum=sum(w.values()),normalization='filtered_minmax',saved_top3=' / '.join(r['iata'] for r in saved[:3])))
        replays.extend(dict(origin_model=role,scenario=f'author_min{threshold}',**r) for r in rows)
        checks.append(dict(check=f'{role}_min{threshold}',status='PASS_WITHIN_EXPORT_PRECISION' if replay_ok else 'MISMATCH_HISTORICAL_DERIVED',rows=len(rows),
            top3_equal=top_equal,
            max_export_score_delta=max(errors),export_precision=3,
            decimal_half_boundary_note='Python/pandas floating sums may round opposite ways exactly at half-ulp decimal boundary'))
    if role=='nastya':
        ids=[i for i in all_ids if olddist[i]>=500]
        z,_=legacy_z(d,ids,anchors=all_ids)
        rows=rank_rows(z,w)
        comparisons.append(summary(role,'labelled_fix_frozen20_scales_min500',rows,'NEW_LABELLED_SCENARIO',
            threshold_km=500,bases='author_rounded_SVO_DME_VKO_SVX',mode='author_scope',profile='author_weights',
            weight_sum=sum(w.values()),normalization='frozen20_legacy_data'))
        replays.extend(dict(origin_model=role,scenario='labelled_fix_frozen20_scales_min500',**r) for r in rows)
    return d,ll

def stress_data(data,stress):
    d=copy.deepcopy(data);cs={c['key']:c for c in d['criteria']}
    def util(v,c):
        z=max(0.,min(1.,(v-c['lo'])/(c['hi']-c['lo'])))
        return 1-z if c['dir']=='-' else z
    for i,row in d['values'].items():
        if stress=='common_neutral':
            for k in ['competitor_hub','ssj_mro','transfer_zone']:row[k].update(u=.5,u_low=.5,u_high=.5)
        if stress=='intro_only':
            u=util(d['stage1']['intro_only'][i],cs['last365_days']);row['last365_days'].update(u=u,u_low=u,u_high=u)
        if stress in ['transfer_low','transfer_high']:
            row['transfer_demand_base']['u']=float(stress=='transfer_high')
        if i=='REN' and stress=='ren_lower':row['pax_2025']['u']=util(951000,cs['pax_2025'])
        if i=='REN' and stress=='ren_extreme':row['pax_2025'].update(u=1.,u_high=1.)
    return d

def stage_replay(data,ll,comparisons,replays,checks):
    groups=defaultdict(list)
    for r in load('tsiri_stage22',MODEL+'final_scores.csv'):
        groups[(r['stress'],int(r['min_dist_km']),r['mode'],r['profile'])].append(r)
    summaries={(r['stress'],int(r['min_dist_km']),r['mode'],r['profile']):r
        for r in load('tsiri_stage22',MODEL+'final_comparison.csv')}
    profiles={p['id']:p['weights'] for p in data['stage1']['profiles']}
    all_ids=[r['iata'] for r in ll]
    dist={r['iata']:min(float(r['dist_msk_km']),float(r['dist_ekb_km'])) for r in ll}
    excluded=set(data['stage1']['strict_excluded'])
    maxerr=0.;count=0
    for key,saved in groups.items():
        stress,threshold,mode,profile=key
        ids=[i for i in all_ids if dist[i]>=threshold and not(mode=='strict_new' and i in excluded)]
        z,lo,hi,unk,ind=author_stage_z(stress_data(data,stress),ids)
        rows=rank_rows(z,profiles[profile],lo,hi,unk,ind)
        assert [r['iata'] for r in rows]==[r['iata'] for r in saved],key
        assert ' / '.join(r['iata'] for r in rows[:3])==summaries[key]['top3'],key
        for a,b in zip(rows,saved):
            for k in ['score','score_low','score_high','unknown_weight_share','indirect_weight_share','uncertain_weight_share']:
                err=abs(a[k]-float(b[k]));maxerr=max(maxerr,err);assert err<TOL,(key,k,err)
            assert a['author_rank_best']==int(b['rank_best']) and a['author_rank_worst']==int(b['rank_worst'])
            count+=1
        scenario='|'.join(map(str,key))
        comparisons.append(summary('tsiri_stage22',scenario,rows,'PASS_ACCEPTED_UTILITY_REPLAY',
            threshold_km=threshold,bases='author_rounded_SVO_DME_VKO_SVX',mode=mode,profile=profile,
            stress=stress,weight_sum=sum(profiles[profile].values()),normalization='frozen20_stage22'))
        replays.extend(dict(origin_model='tsiri_stage22',scenario=scenario,**r) for r in rows)
    checks.append(dict(check='stage22_final140',status='PASS',configurations=len(groups),rows=count,max_abs_delta=maxerr,
        raw_revalidated=False,random_frequencies_replayed=False))
    return profiles

def oldscreen_replay(comparisons,replays,checks):
    d=load('tsiri_historical','context/11_practical_screening/inputs.json')
    coords={r['iata']:(r['lat'],r['lon']) for r in load('tsiri_historical','context/11_practical_screening/coordinates.json')}
    g=d['geography'];pairs=[(x,y) for x in g['north'] for y in g['south']]+[(x,y) for x in g['east'] for y in g['east_south']]
    vals={};new={};details=[]
    def clamp(v):return max(0,min(100,v))
    for c in d['cities']:
        i=c['iata'];v=[]
        for x,y in pairs:
            a,b,c0=hav(coords[x],coords[i]),hav(coords[i],coords[y]),hav(coords[x],coords[y])
            r=(a+b)/c0;ok=g['min_leg_km']<=a<=g['max_leg_km'] and g['min_leg_km']<=b<=g['max_leg_km']
            v.append(max(0,min(1,(g['detour_ceiling']-r)/(g['detour_ceiling']-1))) if ok else 0)
        coverage=sum(v)/len(v)*100;dist=min(hav(coords[i],coords['DME']),hav(coords[i],coords['SVX']))
        vals[i]=dict(market=clamp((c['population_thousands']-500)/10),competition=sum(c['competition_interval'])/2,
            geography=.75*coverage+.25*clamp(dist/g['distance_scale_km']*100),technical=sum(c['technical_interval'])/2,
            basing=sum(c['basing_interval'])/2)
        new[i]=c.get('new_node',True)
    saved=load('tsiri_historical','context/11_practical_screening/ranking.csv');maxerr=0.
    for profile,w in d['weights'].items():
        for scope in ['all','new_node']:
            ids=[i for i in vals if scope=='all' or new[i]]
            rows=rank_rows({i:vals[i] for i in ids},w)
            # Old author tie rule uses IATA; there are no current top3 ties.
            rr=[r for r in saved if r['weights']==profile and r['scope']==scope]
            assert [r['iata'] for r in rows]==[r['iata'] for r in rr]
            for a,b in zip(rows,rr):
                delta=abs(round(a['score'],4)-float(b['score']));maxerr=max(maxerr,delta);assert delta<TOL
            scenario=f'stage11|{profile}|{scope}'
            comparisons.append(summary('tsiri_historical',scenario,rows,'PASS_ARITHMETIC_ROUNDED_EXPORT',
                profile=profile,mode=scope,threshold_km='none',bases='DME_SVX_distance_reward',
                normalization='0_100_fixed_formula',weight_sum=sum(w.values())))
            replays.extend(dict(origin_model='tsiri_historical',scenario=scenario,**r) for r in rows)
    updates=load('tsiri_historical','context/12_network_economics/city_ranking_update_full.csv')
    base=[r for r in saved if r['weights']=='base' and r['scope']=='new_node']
    bygroups=defaultdict(list)
    for r in updates:bygroups[r['case'],r['weights']].append(r)
    for (case,profile),rr in bygroups.items():
        w=dict(d['weights'][profile]);z={r['iata']:{k:float(r[k]) for k in w} for r in base}
        for i,row in z.items():
            if i=='UFA':row['technical']=75
            if case in ['all_technical_equal_100','equal_technical_UFA_basing_80_scenario']:row['technical']=100
            if case=='equal_technical_UFA_basing_80_scenario' and i=='UFA':row['basing']=80
        if case=='omit_technical_weight':
            w['technical']=0;total=sum(w.values());w={k:v/total for k,v in w.items()}
        rows=rank_rows(z,w)
        assert [r['iata'] for r in rows]==[r['iata'] for r in rr]
        for a,b in zip(rows,rr):assert abs(a['score']-float(b['score']))<TOL
        comparisons.append(summary('tsiri_historical',f'stage12|{case}|{profile}',rows,'PASS_ROUNDED_STAGE11_INPUT_REPLAY',
            profile=profile,mode='new_node',threshold_km='none',bases='DME_SVX_distance_reward',
            normalization='0_100_fixed_formula',weight_sum=sum(w.values())))
    checks.append(dict(check='historical_stage11_stage12',status='PASS',stage11_configs=8,stage12_configs=16,
        max_stage11_export_delta=maxerr,raw_revalidated=False))

def controlled(data,ll,profiles,comparisons,checks):
    coords={r['iata']:(float(r['lat']),float(r['lon'])) for r in read_csv(IN/'airport_coordinates.csv')}
    refsets={'historical_SVO_DME_VKO_SVX':['SVO','DME','VKO','SVX'],'case_ZIA_SVX':['ZIA','SVX']}
    ids=[r['iata'] for r in ll];distance={};distance_rows=[];old_deltas=[]
    for label,bases in refsets.items():
        distance[label]={i:min(hav(coords[i],coords[b]) for b in bases) for i in ids}
        for r in ll:
            i=r['iata'];near=min(bases,key=lambda b:hav(coords[i],coords[b]));old=min(float(r['dist_msk_km']),float(r['dist_ekb_km']))
            value=distance[label][i]
            distance_rows.append(dict(iata=i,city=r['city'],reference_set=label,bases='/'.join(bases),nearest=near,
                km_unrounded=value,km_rounded=round(value),author_rounded_km=old,
                delta_to_author_rounded=round(value)-old,
                pass_0=value>=0,pass_300=value>=300,pass_500=value>=500,pass_800=value>=800))
            if label=='historical_SVO_DME_VKO_SVX':old_deltas.append(abs(round(value)-old))
    write_csv('distances.csv',distance_rows)
    support=set(data['stage1']['strict_excluded']);scores_out=[];selection=[]
    cases={}
    for refs,dist in distance.items():
        for threshold in [0,300,500,800]:
            for mode in ['expansion_allowed','strict_new']:
                eligible=[i for i in ids if dist[i]>=threshold and not(mode=='strict_new' and i in support)]
                for profile,w in profiles.items():
                    z,lo,hi,unk,ind=author_stage_z(data,eligible);rows=rank_rows(z,w,lo,hi,unk,ind)
                    label=f'{refs}|{threshold}|{mode}|{profile}';cases[refs,threshold,mode,profile]=rows
                    comparisons.append(summary('controlled_common_stage22',label,rows,'NEW_CONTROLLED_SCENARIO',
                        threshold_km=threshold,bases=refs,mode=mode,profile=profile,stress='base',
                        weight_sum=sum(w.values()),normalization='frozen20_stage22',
                        excluded=' / '.join(i for i in ids if i not in eligible)))
                    scores_out.extend(dict(scenario=label,**r) for r in rows)
                for i in ids:
                    selection.append(dict(reference_set=refs,threshold_km=threshold,mode=mode,iata=i,
                        decision='conditional_pass' if i in eligible else 'excluded',
                        reason='distance' if dist[i]<threshold else 'confirmed_support_strict_new' if mode=='strict_new' and i in support else 'remaining_feasibility_UNKNOWN'))
    write_csv('controlled_scores.csv',scores_out);write_csv('eligibility.csv',selection)
    # Pairwise one-factor deltas, no averaging of incompatible model scores.
    deltas=[]
    for key,rows in cases.items():
        refs,threshold,mode,profile=key
        alternatives=[]
        if threshold in [0,300,500]:alternatives.append(('threshold',(refs,{0:300,300:500,500:800}[threshold],mode,profile)))
        if refs=='historical_SVO_DME_VKO_SVX':alternatives.append(('reference_points',('case_ZIA_SVX',threshold,mode,profile)))
        if mode=='expansion_allowed':alternatives.append(('scope',(refs,threshold,'strict_new',profile)))
        if profile=='balanced':
            for p in profiles:
                if p!='balanced':alternatives.append(('profile',(refs,threshold,mode,p)))
        before={r['iata']:r for r in rows}
        for factor,k2 in alternatives:
            after={r['iata']:r for r in cases[k2]}
            common=set(before)&set(after)
            delta=max(abs(before[i]['score']-after[i]['score']) for i in common)
            if factor!='profile':assert delta<TOL
            deltas.append(dict(factor=factor,before='|'.join(map(str,key)),after='|'.join(map(str,k2)),
                before_top3=' / '.join(r['iata'] for r in rows[:3]),after_top3=' / '.join(r['iata'] for r in cases[k2][:3]),
                excluded=' / '.join(i for i in ids if i in before and i not in after),
                added=' / '.join(i for i in ids if i in after and i not in before),common_score_max_delta=delta))
    write_csv('one_factor_deltas.csv',deltas)
    checks.append(dict(check='controlled_common_data',status='PASS',configs=len(cases),distance_max_rounded_delta=max(old_deltas),
        fixed_score_invariant=True,one_factor_comparisons=len(deltas)))
    return cases

def robustness(data,ll,profiles,comparisons,checks):
    ids=[r['iata'] for r in ll];dist={r['iata']:min(float(r['dist_msk_km']),float(r['dist_ekb_km'])) for r in ll}
    rowsout=[];weightsout=[];bounds=[];matrix=[];changes=[]
    for p,w in profiles.items():
        weightsout.extend(dict(profile=p,criterion=k,weight=v) for k,v in w.items())
    for threshold in [0,500]:
        eligible=[i for i in ids if dist[i]>=threshold]
        z,lo,hi,unk,ind=author_stage_z(data,eligible)
        for profile,w0 in profiles.items():
            nominal=rank_rows(z,w0,lo,hi,unk,ind)
            bounds.extend(dict(threshold_km=threshold,profile=profile,**r) for r in nominal)
            variations=[('leave_one_out',k,[k]) for k,v in w0.items() if v>0]+[('omit_proxy_family','proxy_family',PROXY)]
            for kind,label,drop in variations:
                w={k:(0 if k in drop else v) for k,v in w0.items()}
                rr=rank_rows(z,w,lo,hi,unk,ind)
                scenario=f'{threshold}|{profile}|{kind}|{label}'
                ss=summary('robustness_common_stage22',scenario,rr,'NEW_PREDECLARED_SENSITIVITY',
                    threshold_km=threshold,bases='author_rounded_SVO_DME_VKO_SVX',mode='expansion_allowed',
                    profile=profile,weight_sum=sum(w.values()),omitted=label,kind=kind)
                comparisons.append(ss)
                rowsout.append(dict(**ss,same_top3=set(r['iata'] for r in rr[:3])==set(r['iata'] for r in nominal[:3])))
                if kind=='leave_one_out':changes.append(rowsout[-1])
            # WEATHER is unknown at every city: central common .5 has no ranking content.
            w={k:(0 if k=='bad_weather_days' else v) for k,v in w0.items()}
            nw=rank_rows(z,w,lo,hi,unk,ind)
            assert [r['iata'] for r in nw]==[r['iata'] for r in nominal]
            a=w0['bad_weather_days']/sum(w0.values())
            for r,r0 in zip(nw,nominal):assert abs(r['score']-(r0['score']-.5*a)/(1-a))<TOL
        for i in eligible:
            for c in data['criteria']:
                x=data['values'][i][c['key']]
                matrix.append(dict(threshold_km=threshold,iata=i,criterion=c['key'],raw_value=x['v'],
                    status=x['status'],utility=x['u'],low=x['u_low'],high=x['u_high'],unknown=x['unknown'],indirect=x['indirect'],
                    reference_period=x.get('reference_period',''),source=x.get('s','')))
    write_csv('robustness.csv',rowsout);write_csv('profiles.csv',weightsout);write_csv('unknown_bounds.csv',bounds)
    write_csv('criterion_matrix.csv',matrix)
    # Exact tie regression: all weather-only central .5, or fixed identical .5.
    z={i:{'weather':.5} for i in ids};w={'weather':7}
    fixture=rank_rows(z,w)
    assert all(r['central_rank_min']==1 and r['central_rank_max']==len(ids) for r in fixture)
    assert all(r['rank_worst_inclusive']==len(ids) and r['author_rank_worst']==1 for r in fixture)
    dump('tie_fixture.json',dict(status='PASS',description='Identical fixed weather utilities: all cities tied',
        n=len(ids),author_strict_greater_bounds='1..1',corrected_tie_inclusive_bounds=f'1..{len(ids)}',rows=fixture))
    checks.append(dict(check='predeclared_robustness',status='PASS',loo_configs=len(changes),
        loo_top3_set_changes=sum(not r['same_top3'] for r in changes),
        weather_constant_no_central_rank_effect=True,tie_regression='PASS',profiles=len(profiles)))

def attribution(nastya,data,ll,comparisons):
    ids=[r['iata'] for r in ll if min(float(r['dist_msk_km']),float(r['dist_ekb_km']))>=500]
    oldw={c['key']:c['weight'] for c in nastya['criteria']};neww={c['key']:c['weight'] for c in data['criteria']}
    zold,_=legacy_z(nastya,ids);zfixed,_=legacy_z(nastya,ids,anchors=list(nastya['values']))
    z,lo,hi,unk,ind=author_stage_z(data,ids)
    rows=[];contrib=[];delta=[]
    def add(step,utilities,weights):
        rr=rank_rows(utilities,weights)
        rows.extend(dict(step=step,weight_sum=sum(weights.values()),**r) for r in rr)
        comparisons.append(summary('attribution_local',step,rr,'NEW_LABELLED_DECOMPOSITION',threshold_km=500,
            bases='author_rounded_SVO_DME_VKO_SVX',mode='expansion_allowed',profile=step,weight_sum=sum(weights.values())))
        return rr
    add('0_nastya_original',zold,oldw)
    add('1_only_freeze_20city_scales',zfixed,oldw)
    # One criterion's normalization rule at a time, then one criterion's accepted
    # data/utility overlay at a time; never hide multiple changed columns.
    current=copy.deepcopy(zfixed)
    for c in data['criteria']:
        k=c['key']
        for i in ids:
            v=nastya['values'][i][k]['v']
            if v is None or c.get('constant') or c['hi']<=c['lo']:u=.5
            else:
                u=max(0.,min(1.,(v-c['lo'])/(c['hi']-c['lo'])))
                if c['dir']=='-':u=1-u
            current[i][k]=u
        add('2_scale_rule_'+k,current,oldw)
    for c in data['criteria']:
        k=c['key']
        for i in ids:current[i][k]=z[i][k]
        add('3_accepted_cell_'+k,current,oldw)
    assert current==z
    w=dict(oldw)
    for k in oldw:
        if oldw[k]!=neww[k]:
            w[k]=neww[k];add('4_weight_'+k,z,w)
    assert w==neww
    for i in ['OMS','REN','BAX','KUF']:
        for c in data['criteria']:
            k=c['key'];contrib.append(dict(iata=i,criterion=k,old_weight=oldw[k],new_weight=neww[k],
                nastya_filtered_u=zold[i][k],nastya_fixed_u=zfixed[i][k],stage22_accepted_u=z[i][k],
                old_contribution=oldw[k]*zold[i][k]/sum(oldw.values()),
                new_contribution=neww[k]*z[i][k]/sum(neww.values())))
    # At a fixed accepted utility table, explain the tiny third/fourth gap exactly.
    for c in data['criteria']:
        k=c['key'];v=neww[k]*(z['BAX'][k]-z['KUF'][k])/sum(neww.values())
        delta.append(dict(criterion=k,weight=neww[k],BAX_u=z['BAX'][k],KUF_u=z['KUF'][k],BAX_minus_KUF_contribution=v))
    write_csv('attribution_local.csv',rows);write_csv('leader_contributions.csv',contrib);write_csv('bax_kuf_gap.csv',delta)

def criteria_catalogue(nastya,stage):
    rows=[]
    for role,data in [('nastya',nastya),('tsiri_stage22',stage)]:
        for c in data['criteria']:
            k=c['key'];periods=sorted({str(row[k].get('reference_period','UNSPECIFIED')) for row in data['values'].values()})
            rows.append(dict(origin_model=role,criterion=k,label=c['label'],direction=c['dir'],weight=c['weight'],
                normalized_weight=c['weight']/sum(cc['weight'] for cc in data['criteria']),
                lo=c.get('lo'),hi=c.get('hi'),fill=c.get('fill'),group=c.get('group'),reference_period=' / '.join(periods),
                raw_nulls=sum(row[k]['v'] is None for row in data['values'].values()),
                note=c.get('why','')))
    write_csv('criteria_comparison.csv',rows)

def accepted_cell_arithmetic(data,checks):
    """Validate transformation of stored accepted values, not the external facts."""
    rows=[]
    def utility(v,c):
        if v is None or c.get('constant') or c['hi']<=c['lo']:return .5
        u=max(0.,min(1.,(v-c['lo'])/(c['hi']-c['lo'])))
        return 1-u if c['dir']=='-' else u
    for i,row in data['values'].items():
        for c in data['criteria']:
            k=c['key'];x=row[k];expected=utility(x['v'],c);rule='value_fixed_anchor_or_unknown_neutral'
            if k=='gap_pop':
                expected=(utility(x['raw_low'],c)+utility(x['raw_high'],c))/2;rule='unknown_rail_midpoint'
            if k=='pax_2025' and x['v'] is None and x.get('raw_low') is not None:
                if i=='REN':expected=utility(x['approximate_derived'],c);rule='REN_explicit_rounded_components_assumption'
                else:expected=(utility(x['raw_low'],c)+1)/2;rule='qualified_lower_bound_midpoint_to_frozen_upper_anchor'
            delta=abs(x['u']-expected)
            rows.append(dict(iata=i,criterion=k,rule=rule,accepted_u=x['u'],recomputed_u=expected,delta=delta))
            assert delta<TOL,(i,k,expected,x['u'])
    write_csv('accepted_cell_arithmetic.csv',rows)
    checks.append(dict(check='accepted_utility_cell_arithmetic',status='PASS',cells=len(rows),max_abs_delta=max(x['delta'] for x in rows),
        semantic_or_primary_fact_revalidation=False))

def universe_bridge(data,ll,comparisons,checks):
    """Post-hoc explanation of universe only; retain each model's own scales."""
    old=load('tsiri_historical','context/11_practical_screening/ranking.csv')
    dist={r['iata']:min(float(r['dist_msk_km']),float(r['dist_ekb_km'])) for r in ll}
    w={c['key']:c['weight'] for c in data['criteria']};output=[]
    for scope in ['all','new_node']:
        saved=[r for r in old if r['weights']=='base' and r['scope']==scope]
        old_by={r['iata']:r for r in saved}
        for threshold in [0,500]:
            # Order follows the common frozen twenty-city universe, never refit.
            ids=[r['iata'] for r in ll if r['iata'] in old_by and dist[r['iata']]>=threshold]
            z,lo,hi,unk,ind=author_stage_z(data,ids)
            stage=rank_rows(z,w,lo,hi,unk,ind)
            legacy=rank_rows({i:{'legacy_score':float(old_by[i]['score'])} for i in ids},{'legacy_score':1.})
            for origin,rows in [('bridge_historical_stage11',legacy),('bridge_stage22',stage)]:
                scenario=f'old_{scope}_universe|radius{threshold}'
                comparisons.append(summary(origin,scenario,rows,'NEW_POSTHOC_UNIVERSE_ONLY_DIAGNOSTIC',
                    threshold_km=threshold,bases='author_rounded_SVO_DME_VKO_SVX',mode=f'legacy_{scope}_subset',
                    profile='own_author_base',normalization='each_model_retains_own_fixed_score'))
                output.extend(dict(origin_model=origin,scenario=scenario,**r) for r in rows)
    write_csv('universe_bridge.csv',output)
    checks.append(dict(check='posthoc_universe_bridge',status='PASS_INVARIANT_FILTERING',configs=8,
        diagnostic_only=True,scores_averaged=False))

def main():
    manifest=json.loads((OUT/'source_manifest.json').read_text())
    for r in manifest['inputs']:
        assert hashlib.sha256((OUT/r['local']).read_bytes()).hexdigest()==r['sha256'],r['local']
    assert hashlib.sha256((OUT/manifest['coordinates']['path']).read_bytes()).hexdigest()==manifest['coordinates']['sha256']
    comparisons=[];replays=[];checks=[]
    legacy_replay('front_historical',comparisons,replays,checks)
    nastya,ll=legacy_replay('nastya',comparisons,replays,checks)
    stage=load('tsiri_stage22','data/processed/criteria.json');stage_ll=load('tsiri_stage22','data/processed/longlist.csv')
    assert [r['iata'] for r in ll]==[r['iata'] for r in stage_ll]
    profiles=stage_replay(stage,stage_ll,comparisons,replays,checks)
    accepted_cell_arithmetic(stage,checks)
    oldscreen_replay(comparisons,replays,checks)
    universe_bridge(stage,stage_ll,comparisons,checks)
    controlled(stage,stage_ll,profiles,comparisons,checks)
    robustness(stage,stage_ll,profiles,comparisons,checks)
    attribution(nastya,stage,stage_ll,comparisons)
    criteria_catalogue(nastya,stage)
    write_csv('comparison.csv',comparisons);write_csv('author_replays.csv',replays)
    write_csv('corrected_scores.csv',[row for row in replays if row['origin_model']=='tsiri_stage22' or
        row['scenario']=='labelled_fix_frozen20_scales_min500'])
    dump('projection_corrections.json',dict(
        status='LOCAL_PROJECTIONS_ONLY_COLLEAGUE_SOURCES_UNCHANGED',
        author_snapshots='inputs/<origin_model>/',author_replay='author_replays.csv',
        corrected_projection='corrected_scores.csv',
        stage22='Scores preserved; tie-aware rank_best/rank_worst_inclusive and central min/max added; original author_rank_* retained',
        nastya='Only fixed20 normalization sensitivity is corrected projection; data and weights unchanged, scenario labelled explicitly',
        historical_front='Mismatch preserved, no invented correction to source data',
        numerical_tolerance=TOL,default_stage22_top3_changed=False))
    dump('validation.json',dict(status='COMPLETE_WITH_HISTORICAL_MISMATCH',checks=checks,
        input_hashes_checked=len(manifest['inputs'])+1,comparison_rows=len(comparisons),
        original_pipelines_executed=False,primary_sources_revalidated=False,
        model_outputs_scenario_summary_used=False,
        not_run=['full raw-to-derived pipeline','2000 random weight frequency replay','network economics rerun',
            'current physical basing/slots/MCT/MRO availability verification','roadtime/catchment substitution or diversion estimation']))
    print(json.dumps(dict(status='COMPLETE_WITH_HISTORICAL_MISMATCH',checks=checks,comparison_rows=len(comparisons)),ensure_ascii=False))

if __name__=='__main__':main()
