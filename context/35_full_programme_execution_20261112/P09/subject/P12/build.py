#!/usr/bin/env python3
"""Exact Git blob → local evidence → self-contained dashboard. No network/optimisation."""
import argparse, csv, hashlib, io, json, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PARENT='65cab12d2eae49dc91d1f77dd4860bc9bd7e20d2'
PINS={'PLAN':PARENT,'BASE':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6','FIVE':'c18f7640ea36647a05b39089e5293f22dd009f63','P00R':'b7d74e67dd6c603db049b1915b1afec987e3b458','P02':'d9486f113f074c185a94bcc5c0afeef12ea3574f','P03':'79dc698b99dfe866886d32376ed388e85bdd039c','P04':'620a0ac4bb11763319c4227485f6a3996b91d367','P06':'bc70308fe091c5767dbf26b02d06a7d750a65614'}
parser=argparse.ArgumentParser();parser.add_argument('--results-commit');parser.add_argument('--results-path');args=parser.parse_args()
if bool(args.results_commit)!=bool(args.results_path):parser.error('results-commit and results-path required together')
manifest=[]
def blob(pkg,path,save=True):
 b=subprocess.check_output(['git','show',PINS[pkg]+':'+path]); digest=hashlib.sha256(b).hexdigest()
 dest=ROOT/'inputs'/pkg/path
 if save: dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(b)
 manifest.append({'package':pkg,'commit':PINS[pkg],'path':path,'sha256':digest,'local_path':str(dest.relative_to(ROOT)) if save else None,'collection':'reused_exact_git_blob'})
 return b.decode()
def pkg(k,n): return blob(k,'context/35_full_programme_execution_20261112/'+k+'/'+n)
def rows(s): return list(csv.DictReader(io.StringIO(s)))
def put(path,obj):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
plan='context/34_full_programme_plan_20261112/'
for name in ['common_spec.json','requirements.csv','method_map.csv','demo_requirements.json','variant_research_plan.json','city_research_seed.csv']:
 text=blob('PLAN',plan+name)
 if name=='city_research_seed.csv': seeds=rows(text)
for name in ['common_contract.json','data_horizon_contract.json','clarification_policy.json','input_acceptance.json','parallelism_policy.json']:
 blob('PLAN','context/35_full_programme_execution_20261112/P00/'+name)
base=json.JSONDecoder().raw_decode(blob('BASE','outputs/redwings_panel.html',False).split('const D = ',1)[1])[0]
tpl=blob('BASE','src/dashboard_template.html');blob('BASE','src/build_dashboard.py')
# Reuse author components instead of replacing their visual system.
css=tpl.split('<style>',1)[1].split('/* шаги 2–4 */',1)[0]
(ROOT/'ui_candidate/source/author-components.css').write_text(css.rstrip()+'\n')
blob('FIVE','context/33_five_city_reassessment_20261112/README.txt')
historical={}
for code in ['UFA','GOJ','PEE','CEK','TJM']:
 path='context/33_five_city_reassessment_20261112/cities/'+code+'/'
 decision=json.loads(blob('FIVE',path+'decision.json'))
 claims=rows(blob('FIVE',path+'claims.csv')); sources=rows(blob('FIVE',path+'sources.csv'))
 historical[code]={'decision':decision,'claims':claims,'sources':sources,'commit':PINS['FIVE']}

pkg('P00R','contract_addendum.json');pkg('P00R','schema_patch.csv')
coverage=rows(pkg('P02','city_coverage.csv'));products=rows(pkg('P02','competitor_products.csv'))
summary=json.loads(pkg('P02','build_summary.json'))
upstream_assumptions=json.loads(pkg('P02','assumptions_register.json'))+json.loads(pkg('P04','cost_assumptions.json'))
prices=rows(pkg('P04','cost_ranges.csv'));pkg('P04','support_terms.csv')
pkg('P03','sp_adapter/p06_bound_fragments.json');pkg('P03','sp_adapter/crew_advisory.json')
pkg('P06','producer_contract.json')
for k,n in [('P00R','artifact_manifest.json'),('P02','output_manifest.json'),('P03','sp_adapter/output_manifest.json'),('P04','output_manifest.json'),('P04','schema_adapter_manifest.json'),('P06','output_manifest.json')]:pkg(k,n)
by={c['iata']:c for c in base['cities']}; cov={c['city']:c for c in coverage}
cities=[]
for s in seeds:
 c=by[s['iata']];v=cov[s['iata']]
 cities.append({'iata':s['iata'],'city':s['city'],'lat':c['lat'],'lon':c['lon'],'partial':int(v['partially_evidenced_outbound_markets']),'uncovered':int(v['uncovered_outbound_markets']),'markets':int(v['required_outbound_markets']),'assumption_ids':['P12-UI-01']})
airports={c['iata']:{'lat':c['lat'],'lon':c['lon'],'city':c['city']} for c in base['cities']}
for ds in base['dests'].values():
 for c in ds: airports[c['to']]={'lat':c['lat'],'lon':c['lon'],'city':c['city']}
extensions=json.loads((ROOT/'ui_candidate/data/city_extensions.json').read_text())
for c in extensions['cities']:
 if c['iata'] in {r['iata'] for r in cities}:raise ValueError('City extension cannot silently override an existing city')
 if not c.get('source_refs') or not c.get('assumption_ids'):raise ValueError('New city needs source_refs and assumption_ids')
 if not isinstance(c.get('lat'),(int,float)) or not isinstance(c.get('lon'),(int,float)):raise ValueError('New city needs sourced coordinates')
 for k in ['partial','uncovered','markets']:c.setdefault(k,None)
 cities.append(c);airports[c['iata']]={'lat':c['lat'],'lon':c['lon'],'city':c['city']}
fields=['product_id','origin','destination','carrier','flight','status','row_grain','departure_date','valid_from','valid_to','weekdays_iso','departure_local','arrival_local','aircraft','fare_rub','comparable_basket','baggage','fees_status','open_seats','source_id','source_locator','source_url','period','as_of','retrieved_at','collection','assumption_ids','coverage','method_version','temporal_acceptance','year_2027_2028_use','nominal_seats','operating_carrier_status','notes']
products=[{k:r.get(k) for k in fields} for r in products]
# Keep primary price items with metadata, never extrapolate to future paid costs.
costs=[r for r in prices if r['key'] in ['takeoff_landing','security','terminal_domestic']]
def point(lon,lat): return [(lon-20)/130*1100+20,(74-lat)/36*390+10]
def geom(g):
 out=[]
 polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates'] if g['type']=='MultiPolygon' else []
 for p in polys:
  for ring in p:
   pts=[point(*x[:2]) for x in ring if 15<=x[0]<=180]
   if len(pts)>2:out.append('M'+'L'.join(f'{x:.1f},{y:.1f}' for x,y in pts)+'Z')
 return ''.join(out)
geo=[{'path':geom(f['geometry']),'rus':f['properties'].get('ADM0_A3')=='RUS'} for f in base['geo']['countries']]
data={'version':'P12-source-tranche-v1','as_of':'2026-11-12','city_extension_version':extensions['version'],'cities':cities,'airports':airports,'geo':geo,'historical':historical,'assumptions':upstream_assumptions+json.loads((ROOT/'assumptions_register.json').read_text()),'products':products,'costs':costs,'summary':summary,'pins':PINS,'evaluations':[],'programmes':[],'strategy':None,'release':{'final_results':'NOT_RUN','presentation_rehearsal':'NOT_RUN','P03':'ROOT_ACCEPTANCE_PENDING','P06':'EARLY_INTERFACE_ONLY'}}
if args.results_commit:
 if not re.fullmatch('[a-f0-9]{40}',args.results_commit):parser.error('exact 40hex commit required')
 PINS['RESULT']=args.results_commit;data['result_package']=json.loads(blob('RESULT',args.results_path))
put('ui_candidate/data/source_data.json',data);put('input_manifest.json',{'parent_commit':PARENT,'files':manifest,'new_collection':False})
styles=css+'\n'+(ROOT/'ui_candidate/source/app.css').read_text()
js=(ROOT/'ui_candidate/source/adapter.js').read_text()+'\n'+(ROOT/'ui_candidate/source/app.js').read_text()
page=(ROOT/'ui_candidate/source/template.html').read_text().replace('/* STYLES */',styles).replace('/* DATA */',json.dumps(data,ensure_ascii=False).replace('</','<\\/')).replace('/* CODE */',js)
(ROOT/'ui_candidate/dashboard.html').write_text(page)
print(json.dumps({'cities':len(cities),'products':len(products),'cost_references':len(costs),'input_blobs':len(manifest),'dashboard_bytes':len(page.encode())},ensure_ascii=False))
