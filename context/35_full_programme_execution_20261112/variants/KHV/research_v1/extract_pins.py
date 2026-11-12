import subprocess,csv,io,json,hashlib,pathlib
ROOT=pathlib.Path(__file__).parent
pins={'MODEL':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6','FIVE':'c18f7640ea36647a05b39089e5293f22dd009f63','P00R':'b7d74e67dd6c603db049b1915b1afec987e3b458','P02':'d9486f113f074c185a94bcc5c0afeef12ea3574f','P03':'79dc698b99dfe866886d32376ed388e85bdd039c','P04':'620a0ac4bb11763319c4227485f6a3996b91d367','P06':'982f13d9b6c378ed9581125ecc5c40f17dade6a3'}
manifest=[]
for label,sha in pins.items():
 paths=subprocess.check_output(['git','ls-tree','-r','--name-only',sha],text=True).splitlines()
 if label=='MODEL':paths=[p for p in paths if p.endswith('.csv') and p.startswith(('data/manual/','data/processed/','data/assumptions/'))]
 elif label=='FIVE':paths=[]
 else: paths=[p for p in paths if p.startswith('context/35_full_programme_execution_20261112/'+label+'/') and p.count('/')==3 and p.endswith('.csv')]
 for p in paths:
  b=subprocess.check_output(['git','show',sha+':'+p]);rows=list(csv.DictReader(io.StringIO(b.decode())))
  hits=[]
  for n,r in enumerate(rows,2):
   localkeys=['city','iata','geography_or_airport','airport','airport_iata','base_iata','hub_iata','candidate_iata']
   discriminator=next((r[k] for k in localkeys if k in r),None)
   match=discriminator in ('KHV','Хабаровск') if discriminator else any(v=='KHV' or 'Хабаровск' in v or ':KHV' in v or 'KHV:' in v or '>KHV' in v or 'KHV>' in v for v in r.values())
   if match:hits.append({'source_row_number':n,'source_row_sha256':hashlib.sha256(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'original_row':r})
  if hits:
   out='inputs/'+label+'_'+pathlib.Path(p).stem+'.json';(ROOT/out).write_text(json.dumps(hits,ensure_ascii=False,indent=2)+'\n')
   manifest.append({'source_id':label+'_'+pathlib.Path(p).stem,'commit':sha,'path':p,'git_blob':subprocess.check_output(['git','rev-parse',sha+':'+p],text=True).strip(),'full_source_sha256':hashlib.sha256(b).hexdigest(),'selected_rows':len(hits),'selection':'KHV explicit discriminator or KHV endpoint/name; related market lists from other cities excluded where discriminator exists','output':out})
for label,p in [('P00R','contract_addendum.json'),('P06','producer_contract.json'),('P06','README.md'),('P03','handoff.json'),('P03','aircraft_variants.csv'),('P04','thresholds.csv')]:
 path='context/35_full_programme_execution_20261112/'+label+'/'+p
 try:b=subprocess.check_output(['git','show',pins[label]+':'+path],stderr=subprocess.DEVNULL)
 except subprocess.CalledProcessError:continue
 out='inputs/'+label+'_'+p;(ROOT/out).write_bytes(b);manifest.append({'source_id':label+'_'+p,'commit':pins[label],'path':path,'full_source_sha256':hashlib.sha256(b).hexdigest(),'output':out,'scope':'small shared contract, not fixture'})
# Plan exists at supplied P02 pin; use that exact SHA, not a moving branch.
for p in ['city_research_seed.csv','variant_research_plan.json']:
 path='context/34_full_programme_plan_20261112/'+p; b=subprocess.check_output(['git','show',pins['P02']+':'+path]); obj=list(csv.DictReader(io.StringIO(b.decode()))) if p.endswith('csv') else json.loads(b)
 if p.endswith('csv'):obj=[r for r in obj if 'KHV' in str(r)]
 else:
  def scan(o):
   if isinstance(o,dict):
    if any(v=='KHV' for v in o.values() if isinstance(v,str)): return [o]
    return sum([scan(v) for v in o.values()],[])
   if isinstance(o,list):return sum([scan(v) for v in o],[])
   return []
  obj=scan(obj)
 out='inputs/PLAN_'+p.replace('.csv','.json');(ROOT/out).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');manifest.append({'source_id':'PLAN_'+p,'commit':pins['P02'],'path':path,'full_source_sha256':hashlib.sha256(b).hexdigest(),'output':out,'selection':'KHV only'})
(ROOT/'input_manifest.json').write_text(json.dumps({'pins':pins,'sources':manifest},ensure_ascii=False,indent=2)+'\n')
for r in manifest:print(r['source_id'],r.get('selected_rows','contract'))
