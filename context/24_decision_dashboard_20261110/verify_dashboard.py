#!/usr/bin/env python3
"""Verify data transfer and prepare native browser interaction assertions."""
from pathlib import Path
import json, hashlib, math, re, subprocess
P=Path(__file__).resolve().parent
ROOT=P.parent.parent
d=json.loads((P/'data.json').read_text());h=(ROOT/'decision-dashboard.html').read_text()
checks=[]
def check(ok,label):
    assert ok,label
    checks.append(label)
for s in d['sources']:
    b=subprocess.check_output(['git','show',s['commit']+':'+s['path']],cwd=ROOT)
    check(len(b)==s['bytes'] and hashlib.sha256(b).hexdigest()==s['sha256'],'source '+s['path'])
check(len(d['inventory35'])==35,'35 specifications retained')
check(len(d['finite_networks'])==15,'15 finite unions retained')
check(sum(r['joint_model_gates_pass']=='True' for r in d['finite_networks'])==5,'five necessary gates, not launch')
for r in d['portfolio']:
    calc=float(r['gross_revenue'])-float(r['foregone_RW_revenue'])-float(r['new_pax_variable'])+float(r['saved_old_pax_variable'])-float(r['flight_variable_cost'])
    check(math.isclose(calc,float(r['contribution_before_base_fleet_opportunity']),abs_tol=1e-6),'ledger '+r['portfolio']+'/'+r['scenario']+'/'+r['capture_law'])
for r in d['kover']:
    check(math.isclose(float(r['avoidable_costs'])-float(r['lost_fare_once']),float(r['delta_before_unknown']),abs_tol=1e-6),'cancellation delta '+r['candidate']+'/'+r['scenario']+'/'+r['recipe']+'/'+r['policy'])
    check(math.isclose(float(r['baseline_contribution'])+float(r['delta_before_unknown']),float(r['contribution_after_before_unknown']),abs_tol=1e-6),'cancellation accounting '+r['candidate']+'/'+r['scenario']+'/'+r['recipe']+'/'+r['policy'])
check('/Users/' not in h and not re.search(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b',h),'no local paths or emails')
check(not re.search(r'<(?:script|link)[^>]+(?:src|href)=',h),'offline runtime')
check('100vh' not in h and 'height:100%' not in h,'native layout rules')
check(hashlib.sha256((ROOT/'morning-report.html').read_bytes()).hexdigest()=='8f7ed280f2c255d7690170194ab81ae6c0209096d2225fc38f7bc22ad48486f2','accepted report unchanged')
check(hashlib.sha256((ROOT/'research-report.html').read_bytes()).hexdigest()=='53353f9febbb3e3a5877717f9d87cf5d0eda872b64db54a63f31295a05966057','public report unchanged')
subprocess.run(['node','--check',str(P/'dashboard.js')],check=True,capture_output=True)

qa=r'''<script>
const qaFailures=[];let qaCount=0;function qc(v,msg){qaCount++;if(!v)qaFailures.push(msg);}
function set(id,value){$(id).value=value;}
function near(a,b){return Math.abs(a-b)<.002;}
for(const row of DB.common_rows){const v=affine(row.network,row.scenario,row.recipe,1);qc(near(v.contribution_before_base_fleet_opportunity,+row.contribution_before_base_fleet_opportunity),'common endpoint '+row.network+row.scenario+row.recipe);qc(near(v.sold_journeys,+row.sold_journeys),'journeys endpoint');}
for(const r of DB.affine){const x=Number.isFinite(+r.right)?(+r.left+ +r.right)/2:+r.left+1;const a=affine(r.network,r.scenario,r.recipe,x);qc(Number.isFinite(a.contribution_before_base_fleet_opportunity)&&a.sold_journeys>=-1e-6&&a.segment_pax+1e-6>=a.sold_journeys,'affine region '+r.network+'/'+r.recipe+'/'+r.left);}
const boundary=+DB.boundaries[0].alpha;qc(near(affine('D_SVX8','base','C_TO_N_BLEND',boundary).contribution_before_base_fleet_opportunity,affine('H_UFA_4','base','C_TO_N_BLEND',boundary).contribution_before_base_fleet_opportunity),'rank boundary');
set('lens','portfolio');
for(const sc of ['base','cautious'])for(const law of ['COUNT_ALL_OFFERS','D_GUARD_STANDALONE_CLAIMS'])for(const routes of [true,false])for(const fleet of [true,false])for(const base of [true,false]){set('scenario',sc);set('capture',law);$('route-gate').checked=routes;$('fleet-gate').checked=fleet;$('base-gate').checked=base;renderNetworks();qc(currentRows.every(r=>(!routes||(+r.unique_model_airport_pairs>=8&&+r.unique_model_airport_pairs<=12))&&(!fleet||+r.working_allocated<=4)&&(!base||+r.new_UFA_base_count>0)),'filters');qc(!$('network-map').innerHTML.includes('NaN'),'portfolio map');}
set('scenario','base');set('capture','COUNT_ALL_OFFERS');$('route-gate').checked=true;$('fleet-gate').checked=true;$('base-gate').checked=false;renderNetworks();qc(currentRows.length===5,'five candidates UI');
for(const button of Array.from(document.querySelectorAll('[data-network]'))){selection=button.dataset.network;renderNetworks();qc($('network-map').querySelector('svg').dataset.mapId==='P_'+selection,'selection '+selection);}
$('cost-enabled').checked=true;set('fleet-cost','2.303160396');set('base-cost','0');renderNetworks();let a=currentRows.find(r=>r.portfolio==='D_SVX8'),b=currentRows.find(r=>r.portfolio==='D_previous_best8');qc(near(a.value,b.value),'fleet threshold');set('fleet-cost','');renderNetworks();qc(currentRows.every(r=>Number.isNaN(r.value)),'unknown expense not zero');qc(!$('network-chart').innerHTML.includes('NaN'),'no NaN chart');$('cost-enabled').checked=false;set('fleet-cost','0');
set('lens','common');for(const sc of ['base','cautious'])for(const rp of ['C','N','C_TO_N_BLEND']){set('scenario',sc);set('recipe',rp);resetDemand();for(const x of (rp==='C_TO_N_BLEND'?[0,.5,1]:[0,1,2,3.5])){set('demand',String(x));renderNetworks();qc(currentRows.length===3&&currentRows.every(r=>Number.isFinite(r.value)),'common controls');}}
for(const r of DB.kover){set('k-network',r.candidate);set('k-scenario',r.scenario);set('k-recipe',r.recipe);set('k-policy',r.policy);renderKover();qc($('k-delta').textContent.includes(money(+r.delta_before_unknown)),'Kover own sales delta');}
for(const sc of ['base','cautious'])for(const hub of ['DIRECT','OMS','KUF','REN','GOJ','UFA']){set('author-scenario',sc);set('author-network',hub);renderAuthor();qc($('author-map').querySelector('svg')?.dataset.mapId==='AUTHOR_'+sc+'_'+hub,'author geography');qc(!$('author-map').innerHTML.includes('NaN'),'author map finite');}
for(const policy of ['none','500','strict']){set('city-policy',policy);renderCities();qc($('city-ranking').querySelectorAll('.city-row').length===DB.rankings[policy].length,'rank coverage');}
set('idea-state','all');set('idea-search','');for(const r of DB.inventory35){idea=r.candidate_id;renderIdeas();qc($('idea-title').textContent.startsWith(idea),'all idea cards');qc($('idea-map').querySelector('svg').dataset.mapId===idea,'idea map');}
set('idea-search','zzzzz_no_match');renderIdeas();qc($('idea-list').textContent.includes('ничего'),'empty search');set('idea-search','');set('idea-state','tested');renderIdeas();qc($('idea-list').querySelectorAll('button').length===3,'three tested');set('idea-state','queue');renderIdeas();qc($('idea-list').querySelectorAll('button').length===32,'32 queue');
for(const id of ['networks','cities','kover','ideas','decisions']){document.querySelector('[data-tab="'+id+'"]').click();qc(!$(id).hidden&&document.querySelectorAll('.view:not([hidden])').length===1,'tab '+id);qc(document.documentElement.scrollWidth<=window.innerWidth+1,'overflow '+id);}
set('lens','common');set('scenario','base');set('recipe','C_TO_N_BLEND');resetDemand();set('demand','.68');selection='H_UFA_4';renderNetworks();tab('networks');document.querySelector('[data-zoom="network-map"][data-dir="in"]').click();qc($('network-map').querySelector('svg').style.minWidth==='900px','zoom in');document.querySelector('[data-zoom="network-map"][data-dir="out"]').click();qc($('network-map').querySelector('svg').style.minWidth==='','zoom out');
const savedDraft=draft,savedPersist=persist;try{persist=()=>{};draft={items:[],note:''};$('save-network').click();qc(draft.items.length===1&&draft.items[0].sourceSHA===DB.pins.methods,'save selected network with provenance');$('save-network').click();qc(draft.items.length===1,'no duplicate shortlist');idea='C07';set('idea-state','all');renderIdeas();$('save-idea').click();qc(draft.items.length===2&&draft.items[1].kind==='hypothesis','save hypothesis');const ex=decisionExport();qc(ex.status==='USER_LOCAL_DRAFT_NOT_TEAM_ACCEPTED'&&ex.items.length===2,'export contract');renderDecisions();$('shortlist').querySelector('[data-remove]').click();qc(draft.items.length===1,'remove shortlist item');}finally{draft=savedDraft;persist=savedPersist;renderDecisions();}
document.querySelector('[data-tab=networks]').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));qc(!$('kover').hidden,'keyboard tab switch');tab('networks');
console.log('DASHBOARD_QA '+JSON.stringify({checks:qaCount,failures:qaFailures}));if(qaFailures.length)throw new Error(qaFailures.join(';'));
</script>'''
(P/'qa-interactions.html').write_text(h.replace('</body>',qa+'</body>'))
for name,js in [('kover',"tab('kover');setTimeout(()=>{},0);"),('cities',"tab('cities');"),('ideas',"tab('ideas');"),('decisions',"tab('decisions');")]:
    (P/('qa-'+name+'.html')).write_text(h.replace('</body>','<script>'+js+'</script></body>'))
out={'static_checks':len(checks),'status':'PASS','source_hashes':len(d['sources']),'economic_model_replay':'NOT_RUN','html_sha256':hashlib.sha256(h.encode()).hexdigest(),'native_interaction_QA':'PENDING'}
(P/'checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out))
