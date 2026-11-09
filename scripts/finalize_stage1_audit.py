#!/usr/bin/env python3
"""Single bounded offline integration/reproduction of accepted round-2 rules.
Run with the pinned pandas Python. No fetch, optimizer, workbook, commit or push.
"""
import copy
import csv
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess
import sys

import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
A=ROOT/'context/22_stage1_audit'
B=A/'baseline'
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
import stage1_audit_rules as ar
import longlist_score as ls
from audit_stage1_panel import panel_data, protected_hashes, sha, dump, module


def write_csv(path, rows):
    rows=list(rows)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def data_for_stress(data, stress):
    d=copy.deepcopy(data)
    cs={c['key']:c for c in d['criteria']}
    for i,row in d['values'].items():
        if stress=='common_neutral':
            for k in ar.DOC_KEYS:row[k].update(u=.5,u_low=.5,u_high=.5)
        if stress=='intro_only':
            x=row['last365_days'];u=ar.utility(d['stage1']['intro_only'][i],cs['last365_days'])
            x.update(u=u,u_low=u,u_high=u)
        if stress in ['transfer_low','transfer_high']:
            row['transfer_demand_base']['u']=float(stress=='transfer_high')
        if i=='REN' and stress=='ren_lower':row['pax_2025']['u']=ar.utility(951000,cs['pax_2025'])
        if i=='REN' and stress=='ren_extreme':row['pax_2025'].update(u=1.,u_high=1.)
    return d


def calculate(data,ll,weights,distance,mode,random=True):
    ids=[i for i in ll.index if ll.loc[i,'dist_bases_km']>=distance and not(mode=='strict_new' and i in ar.SUPPORT)]
    z,lo,hi,unknown,indirect=ls.utility_tables(ids,data['criteria'],data['values'])
    w=pd.Series(weights,dtype=float)
    s,sl,sh=(ls.score(t,w) for t in [z,lo,hi])
    out=pd.DataFrame(dict(city=ll.loc[ids,'city'],score=s,score_low=sl,score_high=sh,
        rank_best=[1+sum(sl[j]>sh[i] for j in ids if j!=i) for i in ids],
        rank_worst=[1+sum(sh[j]>sl[i] for j in ids if j!=i) for i in ids],
        unknown_weight_share=(unknown*w).sum(axis=1)/w.sum(),
        indirect_weight_share=(indirect*w).sum(axis=1)/w.sum(),
        uncertain_weight_share=((hi>lo)*w).sum(axis=1)/w.sum()))
    out['boundary_ties']=[sum(sh[j]==sl[i] or sl[j]==sh[i] for j in ids if j!=i) for i in ids]
    out['top3_share_random']=ls.random_top3_hits(z,w)/2000 if random else 0.
    out=out.sort_values('score',ascending=False,kind='stable')
    out.insert(0,'rank',range(1,len(out)+1))
    assert np.isfinite(out.select_dtypes('number')).all().all()
    assert (out.score_low<=out.score+1e-12).all() and (out.score<=out.score_high+1e-12).all()
    return out,z


def validate_node(panel,data,ll,cases):
    _,text=panel_data(panel)
    functions=text[text.index('const CR=D.criteria;'):text.index('\nconst DSTAT=')]
    js='const D='+json.dumps(panel_data(panel)[0])+';\n'+functions
    js+='\nconst cases='+json.dumps(cases)+''';
const results=cases.map(c=>{MIN=c.distance;MODE=c.mode;STRESS=c.stress;W=c.weights;
const q=compute();return {rows:q.rows.map(x=>({iata:x.c.iata,score:x.score,lo:x.lo,hi:x.hi,best:x.best,worst:x.worst,unk:x.unk,indirect:x.indirect,uncertain:x.uncertain,share:x.share,z:x.z})),out:q.out.map(c=>c.iata)};});
let rejected=0;for(const ws of [Object.fromEntries(CR.map(w=>[w.key,0])),{...DEFAULT_W,[CR[0].key]:-1}])try{scoreAll(normalize(D.cities),ws);}catch(e){rejected++;}
D.values._fixture={edge:{v:-5},constant:{v:1}};
const fixtures=[utilityCell({iata:'_fixture'},{key:'edge',lo:0,hi:10,dir:'+'}),utilityCell({iata:'_fixture'},{key:'constant',lo:0,hi:1,dir:'-',constant:true}),utilityCell({iata:'_fixture'},{key:'missing',lo:0,hi:1,dir:'+'})];
const r=rng(42);console.log(JSON.stringify({results,rejected,fixtures,rng:Array.from({length:100},()=>r())}));'''
    proc=subprocess.run(['node'],input=js,text=True,capture_output=True,cwd=ROOT,check=True)
    result=json.loads(proc.stdout)
    errors={k:0. for k in ['score','bounds','normalization','unknown','indirect','uncertain','random_share']}
    count=0
    for case,actual in zip(cases,result['results']):
        d=data_for_stress(data,case['stress'])
        py,z=calculate(d,ll,case['weights'],case['distance'],case['mode'])
        assert list(py.index)==[r['iata'] for r in actual['rows']],case
        assert set(actual['out'])==set(ll.index)-set(py.index)
        for x in actual['rows']:
            i=x['iata'];r=py.loc[i];count+=1
            for k,a,b in [('score',x['score'],r.score),('bounds',x['lo'],r.score_low),('bounds',x['hi'],r.score_high),
                ('unknown',x['unk'],r.unknown_weight_share),('indirect',x['indirect'],r.indirect_weight_share),
                ('uncertain',x['uncertain'],r.uncertain_weight_share),('random_share',x['share'],r.top3_share_random)]:
                errors[k]=max(errors[k],abs(a-b))
            errors['normalization']=max(errors['normalization'],max(abs(x['z'][k]-z.loc[i,k]) for k in z.columns))
            assert (x['best'],x['worst'])==(r.rank_best,r.rank_worst),(case,i,x,r.to_dict())
    r=ls.random_uniform();assert result['rng']==[next(r) for _ in range(100)]
    assert result['rejected']==2
    assert [x['u'] for x in result['fixtures']]==[0,.5,.5]
    assert result['fixtures'][2]['a']==0 and result['fixtures'][2]['b']==1
    assert max(errors.values())<1e-12,errors
    return dict(status='PASS',cases=len(cases),city_comparisons=count,max_abs_errors=errors,
                rng_first_100_equal=True,excluded_sets_equal=True,invalid_weights_rejected=True)


def ledger(data,ll):
    rows=[]
    for i in ll.index:
        for c in data['criteria']:
            x=data['values'][i][c['key']]
            rows.append(dict(iata=i,criterion=c['key'],value=x['v'],status=x['status'],
                raw_fact=x.get('raw_fact',x.get('t') or ''),source=x.get('s') or '',source_date=x['source_date'],
                accessed_date=x['accessed_date'],reference_period=x['reference_period'],scope=x['scope'],
                raw_low=x['raw_low'],raw_high=x['raw_high'],utility=x['u'],utility_low=x['u_low'],utility_high=x['u_high'],
                unknown=x['unknown'],indirect=x['indirect'],coverage=json.dumps(x.get('coverage',{}),ensure_ascii=False),
                uncertainty_reason=x['uncertainty_reason'],note=x['note']))
    write_csv(A/'evidence_ledger.csv',rows)
    accepted=[r for r in rows if (r['criterion']=='rw_support' and r['iata'] in ar.SUPPORT) or
        (r['iata']=='OMS' and r['criterion'] in ['ssj_mro','competitor_hub','rw_support','transfer_zone']) or
        (r['iata'] in ['REN','KUF'] and r['criterion'] in ['pax_2025','transfer_zone','ssj_mro'])]
    write_csv(A/'accepted_research.csv',accepted)
    with (A/'accepted_research.csv').open(newline='') as f:
        read=list(csv.DictReader(f));assert len(read)==len(accepted) and all(None not in r for r in read)
    assert all(r['value']=='' for r in read if r['status']=='UNKNOWN')
    return rows


def attribution(data,ll):
    base=json.loads((B/'data/processed/criteria.json').read_text())
    old=module('old_round2_scoring',B/'src/longlist_score.py')
    ids=list(ll.index[ll.dist_bases_km>=500])
    results=[]
    def add(label,crit,vals,engine,mode='expansion_allowed'):
        ii=[i for i in ids if not(mode=='strict_new' and i in ar.SUPPORT)]
        z,_=engine.normalize(ii,crit,vals);w=pd.Series({c['key']:c['weight'] for c in crit},dtype=float)
        scores=engine.score(z,w).sort_values(ascending=False,kind='stable')
        for rank,(i,s) in enumerate(scores.items(),1):results.append(dict(step=label,rank=rank,iata=i,score=s))
    add('0_baseline',base['criteria'],base['values'],old)
    # Accepted data + uncertainty central choices, retain legacy filtered scales and weights.
    v=copy.deepcopy(data['values'])
    for i,row in v.items():
        for c in base['criteria']:
            k=c['key'];x=row[k]
            if k=='gap_pop':x['v']=(x['raw_low']+x['raw_high'])/2
            if k=='pax_2025' and i=='REN':x['v']=951100
            if k=='pax_2025' and i=='GOJ':x['v']=(1400000+12500000)/2
    add('1_data_unknown_central',base['criteria'],v,old)
    crit=copy.deepcopy(base['criteria'])
    for c,new in zip(crit,data['criteria']):c.update(lo=new['lo'],hi=new['hi'])
    add('2_fixed_scales',crit,data['values'],ls)
    add('3_proposed_weights',data['criteria'],data['values'],ls)
    add('4_strict_new_eligibility',data['criteria'],data['values'],ls,'strict_new')
    write_csv(A/'attribution.csv',results)
    return results


def main():
    def offline(*a,**k):raise RuntimeError('No network permitted in round2')
    socket.socket.connect=offline
    before=protected_hashes();oldpanel,_=panel_data(ROOT/'outputs/redwings_panel.html')
    baseline_manifest=json.loads((B/'manifest.json').read_text())
    for rel,h in baseline_manifest['files'].items():assert sha(B/rel)==h['sha256']
    ll=pd.read_csv(ROOT/'data/processed/longlist.csv').set_index('iata')
    ll['dist_bases_km']=ll[['dist_msk_km','dist_ekb_km']].min(axis=1)
    assert list(ll.index)==list(json.loads((B/'data/processed/criteria.json').read_text())['values'])
    config=dict(status='ROUND2_ACCEPTED_INTEGRATION_PROPOSAL_NOT_TEAM_APPROVED',source_commit=baseline_manifest['source_commit'],
        methodology=['rules.json','recommended_weights.csv','weight_profiles.json','integration_decisions.md','main_source_checks.md'],
        accepted_research='accepted_research.csv',evidence_ledger='evidence_ledger.csv',
        reproduce='python scripts/finalize_stage1_audit.py',scope='stage1_only',ren_refinement='rounded_components_951000_951200_not_exact',
        no_network=True)
    dump(A/'accepted_model_inputs.json',config)
    dump(A/'model_inputs.json',config)
    dump(A/'model_rules.json',dict(status='ROUND2_RULES_APPLIED',rules='context/22_stage1_audit/rules.json',primary_min_dist_km=500,scope_exclusions={'expansion_allowed':[],'strict_new':ar.SUPPORT},profiles='context/22_stage1_audit/weight_profiles.json',normalization='frozen_20_city_anchors',ren_override='rounded_component_assumption',unknown_normalized_interval=[0,1],seed=42,random_samples=2000))
    data=ar.build(ll)
    kov=pd.read_csv(ROOT/'data/processed/kover_days.csv').set_index('iata')
    data['stage1']['intro_only']={i:int(kov.loc[i,'last365_days_intro']) for i in ll.index}
    dump(ROOT/'data/processed/criteria.json',data)
    evidence=ledger(data,ll)
    ps=data['stage1']['profiles'];assert len(ps)==5 and len(data['criteria'])==18
    for p in ps:
        assert sum(p['weights'].values())==100 and p['weights']['dist_bases_km']==p['weights']['rostec_link']==0
    assert sum(c['weight'] for c in data['criteria'] if c['group']=='proxy_market')==45
    summary=[];allrows=[];cases=[]
    stresses=['base','common_neutral','intro_only','ren_lower','ren_extreme','transfer_low','transfer_high']
    for stress in stresses:
        d=data_for_stress(data,stress)
        for distance in [500,0]:
            for mode in ['expansion_allowed','strict_new']:
                for p in ps:
                    out,z=calculate(d,ll,p['weights'],distance,mode)
                    top=list(out.index[:3]);gap=float(out.score.iloc[2]-out.score.iloc[3])
                    summary.append(dict(stress=stress,min_dist_km=distance,mode=mode,profile=p['id'],n=len(out),
                        top3=' / '.join(top),top3_cities=' / '.join(out.city.head(3)),third_fourth_gap=gap,
                        score1=out.score.iloc[0],score2=out.score.iloc[1],score3=out.score.iloc[2]))
                    frame=out.reset_index().rename(columns={'index':'iata'})
                    for row in frame.to_dict('records'):allrows.append(dict(stress=stress,min_dist_km=distance,mode=mode,profile=p['id'],**row))
                    cases.append(dict(stress=stress,distance=distance,mode=mode,weights=p['weights']))
                    if stress=='base' and mode=='expansion_allowed' and p['id']=='balanced':
                        suffix='_min500' if distance else ''
                        out.join(z).to_csv(ROOT/f'data/processed/longlist_scores{suffix}.csv',index_label='iata')
    # Scores for a surviving city must not change with an eligibility-only filter.
    for profile in data['stage1']['profiles']:
        ww=profile['weights']
        full,_=calculate(data,ll,ww,0,'expansion_allowed',random=False)
        filtered,_=calculate(data,ll,ww,500,'strict_new',random=False)
        assert np.max(np.abs(full.loc[filtered.index,'score']-filtered.score))<1e-14
    # Refresh the standard one-weight diagnostic files too; no stale baseline results.
    for distance in [0,500]:
        out,z=calculate(data,ll,ps[0]['weights'],distance,'expansion_allowed',random=False)
        weights=pd.Series(ps[0]['weights'],dtype=float);base=set(out.index[:3]);sens=[]
        for k in weights.index:
            if weights[k]==0:continue
            for factor in [.5,1.5]:
                w=weights.copy();w[k]*=factor
                top=list(ls.score(z,w).sort_values(ascending=False,kind='stable').index[:3])
                sens.append(dict(weight=k,factor=factor,top3=' / '.join(top),same_as_base=set(top)==base))
        suffix='_min500' if distance else ''
        write_csv(ROOT/f'data/processed/longlist_sensitivity{suffix}.csv',sens)
    write_csv(A/'final_comparison.csv',summary)
    write_csv(A/'final_scores.csv',allrows)
    # Authoritative scenario outputs also replace historical generic weight-scenario exports.
    for distance in [500,0]:
        suffix='_min500' if distance else ''
        rows=[s for s in summary if s['stress']=='base' and s['min_dist_km']==distance]
        write_csv(ROOT/f'data/processed/longlist_scenarios{suffix}.csv',rows)
    att=attribution(data,ll)
    from stage1_audit_report import write_reports
    write_reports(ROOT,data,summary,att)
    dash=module('round2_dashboard',ROOT/'src/build_dashboard.py');dash.stage1_only()
    panel=ROOT/'outputs/redwings_panel.html'
    parity=validate_node(panel,data,ll,cases)
    # Meaningful invariant cases independent of the accepted precomputed utility overlay.
    crit=[dict(key='x',dir='+',lo=0,hi=10),dict(key='y',dir='-',lo=0,hi=1),dict(key='c',dir='-')]
    vals={'A':{'x':{'v':-5},'y':{'v':2},'c':{'v':7}},'B':{'x':{'v':20},'c':{'v':7}}}
    z,lo,hi,unk,ind=ls.utility_tables(['A','B'],crit,vals)
    assert z.x.tolist()==[0,1] and z.y.tolist()==[0,.5] and z.c.tolist()==[.5,.5]
    assert lo.loc['B','y']==0 and hi.loc['B','y']==1 and unk.loc['B','y']
    assert data['values']['OMS']['competitor_hub']['v'] is None
    assert data['values']['CEK']['competitor_hub']['indirect']
    assert data['values']['OMS']['ssj_mro']['u']==1
    assert all(data['values'][i]['bad_weather_days']['v'] is None for i in ll.index)
    assert utility_sign_check()
    for bad in [pd.Series({'x':0.,'y':0.,'c':0.}),pd.Series({'x':-1.,'y':1.,'c':1.})]:
        try:ls.score(z,bad)
        except ValueError:pass
        else:raise AssertionError('Invalid Python weights accepted')
    fixture=pd.Series([1.,.8,.50041,.50049,0.],index=list('ABCDE'))
    assert list(fixture.sort_values(ascending=False,kind='stable').index[:3])==['A','B','D']
    assert ls.ranks(pd.Series([1.,1.,1.])).tolist()==[1,2,3]
    subprocess.run([sys.executable,'tests/test_stage1_weather.py'],cwd=ROOT,check=True)
    newpanel,_=panel_data(panel)
    nonstage=[k for k in oldpanel if k not in ['criteria','values','weights','meta','stage1']]
    assert all(oldpanel[k]==newpanel[k] for k in nonstage)
    assert before==protected_hashes(),'Protected upstream/raw/Excel changed'
    for rel,h in baseline_manifest['files'].items():assert sha(B/rel)==h['sha256']
    # Deterministic rerun of accepted integration + results (not a fresh research pass).
    repeat=ar.build(ll);repeat['stage1']['intro_only']=data['stage1']['intro_only'];assert repeat==data
    repeat_scores,_=calculate(repeat,ll,ps[0]['weights'],500,'expansion_allowed')
    exported=pd.read_csv(ROOT/'data/processed/longlist_scores_min500.csv').set_index('iata')
    pd.testing.assert_frame_equal(repeat_scores,exported[repeat_scores.columns],check_dtype=False,atol=1e-14,rtol=0,check_names=False)
    dump(A/'final_validation.json',dict(status='PASS_WITH_DECLARED_LIMITATIONS',scope='stage1_only_proposed_methodology',
        panel=parity,profiles=5,base_scenarios=20,total_scenarios=len(summary),
        deterministic_repeat=True,baseline_immutable=True,filter_only_scores_invariant=True,
        frozen_anchors_unknown_clipping_constant_tests=True,rounding_and_stable_ties=True,protected_files=before,nonstage_panel_payload_unchanged=True,
        weather_fixture='PASS',weather_archives_available=0,weather_current_values='UNKNOWN_FULL_UTILITY_INTERVAL',
        qualified_ren_exact_value='UNKNOWN',ren_central='951100 derived rounded-component assumption; raw fact >951000',
        full_real_world_uncertainty='NOT_COMPLETED: missing source reporting, hourly weather, OD conversion and joint feasibility; encoded bounds are scenario bounds only',
        transfer_pair_scenarios='NOT_AVAILABLE: only stored aggregate base; full utility [0,1] used',
        zia_svx_reference_sensitivity='NOT_COMPLETED: no frozen raw coordinates; primary historical reference preserved',
        python=sys.version,node=subprocess.check_output(['node','--version'],cwd=ROOT,text=True).strip(),
        pandas=pd.__version__,numpy=np.__version__,review_priorities={k:'implemented_with_declared_data_limits' for k in ['R1','R2','R3','R4','R5','R6']}))
    manifest=dict(config=config,source_commit=config['source_commit'],baseline_manifest_sha256=sha(B/'manifest.json'),
                  files={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in [
                      ROOT/'src/stage1_audit_rules.py',ROOT/'src/longlist_score.py',ROOT/'src/build_criteria.py',
                      ROOT/'src/catchment_extra.py',ROOT/'src/dashboard_template.html',ROOT/'src/build_dashboard.py',
                      ROOT/'scripts/finalize_stage1_audit.py',ROOT/'tests/test_stage1_weather.py',
                      A/'accepted_model_inputs.json',A/'model_inputs.json',A/'model_rules.json',A/'final_validation.json',
                      A/'integration_decisions.md',A/'main_source_checks.md',A/'methodology.md',
                      ROOT/'scripts/audit_stage1_panel.py',ROOT/'src/build_longlist.py',
                      A/'accepted_research.csv',A/'evidence_ledger.csv',A/'rules.json',A/'recommended_weights.csv',A/'weight_profiles.json',
                      ROOT/'data/processed/criteria.json',A/'final_comparison.csv',A/'final_scores.csv',A/'attribution.csv',A/'brief.md',A/'summary.html',
                      ROOT/'scripts/stage1_audit_report.py',ROOT/'docs/25_step1_open_questions.md',ROOT/'README.md',panel]})
    dump(A/'final_manifest.json',manifest)
    print(json.dumps(dict(status='PASS_WITH_DECLARED_LIMITATIONS',panel=parity,
                         primary=[s for s in summary if s['stress']=='base' and s['profile']=='balanced']),ensure_ascii=False))


def utility_sign_check():
    c=dict(dir='-',lo=0,hi=1)
    return ar.utility(.5,c)<ar.utility(.25,c)

if __name__=='__main__':main()
