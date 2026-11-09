import os,sys,json,hashlib,subprocess,re,copy,math
from pathlib import Path
ROOT=Path.cwd(); A=ROOT/'context/22_stage1_audit'; O=A/'acceptance'
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import pandas as pd
import stage1_audit_rules as ar
import longlist_score as ls
import finalize_stage1_audit as f
from catchment_extra import weather_counts,weather
from audit_stage1_panel import panel_data

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory():
    return {str(p.relative_to(ROOT)):digest(p) for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and 'acceptance' not in p.parts and p.name not in ['final_acceptance.md','final_acceptance.json']}
before=inventory();(O/'before_hashes.json').write_text(json.dumps(before,indent=2))
d=json.loads((ROOT/'data/processed/criteria.json').read_text()); cs=d['criteria']; vals=d['values']
ll=pd.read_csv(ROOT/'data/processed/longlist.csv').set_index('iata');ll['dist_bases_km']=ll[['dist_msk_km','dist_ekb_km']].min(axis=1)
assert ar.build(ll)==d
panel,txt=panel_data(ROOT/'outputs/redwings_panel.html'); basepanel,_=panel_data(A/'baseline/outputs/redwings_panel.html')
assert all(panel[k]==d[k] for k in d)
assert all(panel[k]==basepanel[k] for k in basepanel if k not in ['criteria','values','weights','meta','stage1'])
man=json.loads((A/'final_manifest.json').read_text());assert all(digest(ROOT/p)==v['sha256'] for p,v in man['files'].items())
bm=json.loads((A/'baseline/manifest.json').read_text());assert all(digest(A/'baseline'/p)==v['sha256'] for p,v in bm['files'].items())
protected=json.loads((A/'final_validation.json').read_text())['protected_files'];assert all(digest(ROOT/p)==h for p,h in protected.items())
# Verify protected tracked files against Git HEAD as well, independently of validation manifest.
tracked_protected=0
for p in protected:
    pr=subprocess.run(['git','show','HEAD:'+p],capture_output=True,cwd=ROOT)
    if pr.returncode==0:
        assert hashlib.sha256(pr.stdout).hexdigest()==digest(ROOT/p),p
        tracked_protected+=1
# independent scalar normalization, not production utility()/score()
def norm(v,c):
    if v is None or c.get('constant') or c['hi']<=c['lo']:return .5
    u=min(1,max(0,(v-c['lo'])/(c['hi']-c['lo'])))
    return 1-u if c['dir']=='-' else u
base=json.loads((A/'baseline/data/processed/criteria.json').read_text())
weak=0;zeros=[]
for i,row in vals.items():
    for c in cs:
        k=c['key'];x=row[k]; v=x['v']; expected=norm(v,c)
        if k=='gap_pop':expected=(norm(x['raw_low'],c)+norm(x['raw_high'],c))/2
        if k=='pax_2025' and x['uncertainty_reason']=='qualified_lower_bound':expected=(norm(x['raw_low'],c)+1)/2
        if i=='REN' and k=='pax_2025':expected=norm(951100,c)
        assert abs(x['u']-expected)<1e-14,(i,k,x['u'],expected)
        assert 0<=x['u_low']<=x['u']<=x['u_high']<=1
        if x['status']=='UNKNOWN':assert v is None and (x['u_low'],x['u_high'])==(0,1)
        old=base['values'][i][k]['v']
        if (k=='competitor_hub' and old in [.25,.75]) or (k=='ssj_mro' and old==.5 and i!='OMS'):
            assert v is None and x['u']==.5 and x['u_low']==0 and x['u_high']==1;weak+=1
        if v==0 and k in ['ssj_mro','transfer_zone','competitor_hub','rw_support','rostec_link']:zeros.append([i,k,x.get('t'),x.get('s')])
assert vals['REN']['pax_2025']['raw_fact']=='>951000' and vals['REN']['pax_2025']['v'] is None
assert vals['OMS']['ssj_mro']['reference_period']=='2024-12-03'
assert d['stage1']['strict_excluded']==['KUF','KZN','AER','MCX']
assert all(vals[i]['bad_weather_days']['v'] is None for i in ll.index)
# All 140 saved cases independently summed from inspected cell utilities.
comparison=pd.read_csv(A/'final_comparison.csv'); scores=pd.read_csv(A/'final_scores.csv'); cases=[]; results=[]; maxerr=0
for r in comparison.to_dict('records'):
    p=next(p for p in d['stage1']['profiles'] if p['id']==r['profile']);w=p['weights']
    assert sum(w.values())==100 and w['dist_bases_km']==0
    rows=[]
    for i in ll.index:
        if ll.loc[i,'dist_bases_km']<r['min_dist_km'] or (r['mode']=='strict_new' and i in d['stage1']['strict_excluded']):continue
        us=[];los=[];his=[]
        for c in cs:
            k=c['key'];x=vals[i][k];u,a,b=x['u'],x['u_low'],x['u_high'];st=r['stress']
            if st=='common_neutral' and k in ['competitor_hub','ssj_mro','transfer_zone']:u=a=b=.5
            if st=='intro_only' and k=='last365_days':u=a=b=norm(d['stage1']['intro_only'][i],c)
            if st=='transfer_low' and k=='transfer_demand_base':u=0
            if st=='transfer_high' and k=='transfer_demand_base':u=1
            if i=='REN' and k=='pax_2025' and st=='ren_lower':u=norm(951000,c)
            if i=='REN' and k=='pax_2025' and st=='ren_extreme':u=b=1
            us.append(u*w[k]/100);los.append(a*w[k]/100);his.append(b*w[k]/100)
        rows.append(dict(iata=i,score=sum(us),lo=sum(los),hi=sum(his)))
    rows.sort(key=lambda x:-x['score']);assert ' / '.join(x['iata'] for x in rows[:3])==r['top3']
    assert abs(rows[2]['score']-rows[3]['score']-r['third_fourth_gap'])<1e-14
    saved=scores[(scores.stress==r['stress'])&(scores.profile==r['profile'])&(scores['mode']==r['mode'])&(scores.min_dist_km==r['min_dist_km'])].set_index('iata')
    for x in rows:
        s=saved.loc[x['iata']]; maxerr=max(maxerr,abs(s.score-x['score']),abs(s.score_low-x['lo']),abs(s.score_high-x['hi']))
        assert s.rank_best==1+sum(y['lo']>x['hi'] for y in rows if y is not x)
        assert s.rank_worst==1+sum(y['hi']>x['lo'] for y in rows if y is not x)
    if r['stress'] in ['base','common_neutral','intro_only']:
        cases.append(dict(distance=r['min_dist_km'],mode=r['mode'],stress=r['stress'],weights=w));results.append(rows)
assert maxerr<1e-14
# Execute actual shipped JS, not the template or a rewritten JS scorer.
js='const D='+json.dumps(panel)+';\n'+txt[txt.index('const CR=D.criteria;'):txt.index('\nconst DSTAT=')]
js+='\nconst cases='+json.dumps(cases)+''';
const actual=cases.map(c=>{MIN=c.distance;MODE=c.mode;STRESS=c.stress;W=c.weights;return compute().rows.map(x=>({iata:x.c.iata,score:x.score,lo:x.lo,hi:x.hi}));});
STRESS='base';
D.values.fixture={clip:{v:25},negative:{v:0},constant:{v:8}};
const fixtures=[utilityCell({iata:'fixture'},{key:'clip',lo:0,hi:10,dir:'+'}),utilityCell({iata:'fixture'},{key:'negative',lo:0,hi:1,dir:'-'}),utilityCell({iata:'fixture'},{key:'constant',lo:0,hi:10,dir:'-',constant:true}),utilityCell({iata:'fixture'},{key:'missing',lo:0,hi:1,dir:'+'})];
const stable=top3([1,.8,.50041,.50049,0]);
MIN=500;MODE='expansion_allowed';W=Object.fromEntries(CR.map(c=>[c.key,c.key==='h24'?100:0]));
const ties=compute().rows.map(x=>({iata:x.c.iata,rank:x.rank,best:x.best,worst:x.worst,score:x.score,tied:x.tied}));
console.log(JSON.stringify({actual,fixtures,stable,ties}));'''
j=json.loads(subprocess.run(['node'],input=js,capture_output=True,text=True,check=True,cwd=ROOT).stdout)
js_error=0
for got,expected in zip(j['actual'],results):
    assert [x['iata'] for x in got]==[x['iata'] for x in expected]
    for x,y in zip(got,expected):
        for k in ['score','lo','hi']:js_error=max(js_error,abs(x[k]-y[k]))
assert js_error<1e-14 and [x['u'] for x in j['fixtures']]==[1,1,.5,.5] and j['stable']==[0,1,3]
assert j['fixtures'][3]['a']==0 and j['fixtures'][3]['b']==1
# Independent Python fixtures: explicit fixed anchors, constants, missing, exact rank ties.
c=[dict(key='x',lo=0,hi=10,dir='+'),dict(key='y',lo=0,hi=1,dir='-'),dict(key='c',lo=0,hi=10,dir='-',constant=True)]
v={'A':{'x':{'v':25},'y':{'v':0},'c':{'v':8}},'B':{'x':{'v':-3}}}
z,lo,hi,_,_=ls.utility_tables(['A','B'],c,v); assert list(z.loc['A'])==[1,1,.5] and list(z.loc['B'])==[0,.5,.5]
assert ls.utility_tables(['B'],c,v)[0].equals(z.loc[['B']])
assert ls.ranks(pd.Series([.5,.5,.5])).tolist()==[1,2,3]
# Read-only production scorer on an attainable panel tie configuration.
tie_weights={c['key']:100 if c['key']=='h24' else 0 for c in cs}
tie_py,_=f.calculate(d,ll,tie_weights,500,'expansion_allowed',random=False)
tie_mismatch=tie_py[tie_py['rank']>tie_py.rank_worst][['rank','rank_best','rank_worst']].to_dict('index')
wc=weather_counts([('a',-9999,-9999),('b',-210,-9999),('b',-9999,130),('c',0,10),('d',None,140)],-20,12)
assert wc==dict(frost=1,wind=2,either=1,valid_temp_days=2,valid_wind_days=3,valid_joint_days=2,record_days=4,observations=5),wc
assert all(x['bad_weather_days'] is None for x in weather().values())
subprocess.run([sys.executable,'-B','tests/test_stage1_weather.py'],check=True,cwd=ROOT)
# Standard CSVs and actual score values.
for distance in [0,500]:
    out,_=f.calculate(d,ll,d['stage1']['profiles'][0]['weights'],distance,'expansion_allowed',random=False)
    csv=pd.read_csv(ROOT/('data/processed/longlist_scores'+('_min500' if distance else '')+'.csv')).set_index('iata')
    assert list(csv.index)==list(out.index) and max(abs(csv.score-out.score))<1e-14
assert inventory()==before
out=dict(status='COMPUTATION_PASS_WITH_TIE_BOUND_DEFECT',cases_independent=140,js_cases=len(cases),score_max_error=maxerr,js_max_error=js_error,weak_cells_checked=weak,tracked_protected_checked=tracked_protected,manifest_files=len(man['files']),payload_unchanged=True,build_equal=True,weather_fixture=wc,raw_zero_cells=zeros,tie_defect=tie_mismatch,js_tie_example=j['ties'][:5],common_neutral=comparison[(comparison.stress=='common_neutral')&(comparison.min_dist_km==500)&(comparison['mode']=='expansion_allowed')].to_dict('records'),source_unchanged=True)
(O/'results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
