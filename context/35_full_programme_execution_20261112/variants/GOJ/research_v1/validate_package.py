"""Structural/provenance checks only; not independent economic acceptance."""
import csv,hashlib,json,pathlib,subprocess
from collections import Counter,defaultdict
ROOT=pathlib.Path(__file__).resolve().parent
def read(name):return json.loads((ROOT/name).read_text())
def csvread(name):return list(csv.DictReader((ROOT/name).open()))
checks=[]
def check(name,passed,detail):checks.append({'check':name,'pass':bool(passed),'detail':detail})
pins=read('source_pins.json');rows=read('goj_source_rows.json')
originals={}
for m in pins['inputs']:
 b=subprocess.check_output(['git','show',m['commit']+':'+m['path']])
 originals[m['package']+'/'+m['path'].split('/')[-1]]=b
 check('sourceblob:'+m['package']+'/'+m['path'].split('/')[-1],hashlib.sha256(b).hexdigest()==m['sha256'],'Exact supplied SHA read; no moving branch used')
for k,rr in rows.items():
 for x in rr:
  b=json.dumps(x['row'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
  assert hashlib.sha256(b).hexdigest()==x['row_sha256'],(k,x['source_row_id'])
 if k=='PLAN/legacy_hypotheses':
  original=json.loads(originals['P00R/variant_research_plan.json'])['legacy_hypotheses']
  assert all(original[x['source_row_number']-1]==x['row'] for x in rr),k
 else:
  original=list(csv.DictReader(originals[k].decode('utf-8-sig').splitlines()))
  assert all(original[x['source_row_number']-2]==x['row'] for x in rr),k
check('rowhashes',True,dict((k,len(v)) for k,v in rows.items()))
for r in read('live_receipts.json'):
 path=r.get('text_path',r.get('path'))
 if path:
  h=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
  check('publicread:'+r['source_id'],h==r.get('text_sha256',r.get('raw_sha256')),'Saved source text/PDF matches receipt; access not forecast')
required=['case.json','evidence.csv','market_deltas.csv','hypotheses.json','programme_candidates.json','comparison_requests.csv','assumptions.csv','readiness.json','handoff.json']
check('requiredoutputs',all((ROOT/f).exists() for f in required),required)
assumptions={r['assumption_id'] for r in csvread('assumptions.csv')}
ev={r['evidence_id'] for r in csvread('evidence.csv')}
hyps=read('hypotheses.json')['hypotheses'];ps=read('programme_candidates.json')['programmes'];pids={p['programme_id'] for p in ps}
check('hypothesisoutcomes',all(h['outcome'] and h['revisit_condition'] and h['counterfactual'] and h['distinguishing_test'] and h['source'] for h in hyps),len(hyps))
check('evidencereferences',all(set(h['source'])<=ev for h in hyps),'All hypothesis signal references resolve')
check('assumptionrefs',all(set(p['assumption_ids'])<=assumptions for p in ps),'Every programme has an assumption register')
check('programmehyprefs',all(set(h['programme_ids'])<=pids for h in hyps),'All programmes referenced by local hypotheses exist')
cal=csvread('programme_calendar.csv');keys=[(r['programme_id'],r['design_date'],r['design_tail'],r['leg_sequence']) for r in cal]
check('unique_designlegs',len(keys)==len(set(keys)),len(cal))
for pid in pids:
 groups=defaultdict(list)
 for r in cal:
  if r['programme_id']==pid:groups[(r['design_date'],r['design_tail'])].append(r)
 valid=True
 for key,rr in groups.items():
  rr.sort(key=lambda r:int(r['leg_sequence']))
  valid &= all(a['destination_airport']==b['origin_airport'] for a,b in zip(rr,rr[1:]))
  valid &= rr[0]['origin_airport']==rr[-1]['destination_airport']
 check('closed_designrotations:'+pid,valid,len(groups))
def legs(pid):return Counter((r['design_date'],r['origin_airport'],r['destination_airport']) for r in cal if r['programme_id']==pid)
check('P01_P02_same_airlegs',legs('GOJ-P01')==legs('GOJ-P02'),'Same date/airleg multiset, different order/basing; no assumed block-hour saving')
check('P03_P04_same_airlegs',legs('GOJ-P03')==legs('GOJ-P04'),'Same date/airleg multiset, through products explicitly differ')
monthly=csvread('programme_monthly_drivers.csv')
expected_months={f'{y}-{m:02}' for y in [2027,2028] for m in range(1,13)}
check('24months_per_programme',all(sum(r['programme_id']==p for r in monthly)==24 and {r['month'] for r in monthly if r['programme_id']==p}==expected_months for p in pids),len(monthly))
check('unknownUTCnotadmitted',all(r['departure_utc']=='UNKNOWN' and r['physical_inventory_id']=='NOT_BOUND' for r in cal),'No fabricated physical allocation/clock or capacity admission')
evt=[r for r in cal if r['programme_id']=='GOJ-P06']
check('event4legs_existingonly',len(evt)==4 and {r['design_date'] for r in evt}=={'2027-05-30','2027-06-03'},'2 design RT before new SJ H2; existing/partner/donor gate in specification')
legacy_ids={x['row']['candidate_id'] for x in rows['PLAN/legacy_hypotheses']}
referenced={a for h in hyps for a in h['ancestorIDs']}
check('legacylineage',legacy_ids<=referenced,'All 7 local legacy candidates mapped, including resilience C34')
check('no_money_winner',all(p['money_result'] is None and p['forecast_journeys'] is None for p in ps),'No local substitute for P05/P06')
check('tariff_visual', (ROOT/'live/GOJ-L16-p12.png').exists(),'Page12 RRJ95B inspected; source-only image, no PDF authoring')
check('stageBnotaccepted',read('readiness.json')['economic_comparison']=='NOT_RUN','Checks validate artifact boundaries, not market/financial feasibility')
result={'status':'PASS_STAGE_A_PACKAGE_INTEGRITY_ONLY' if all(c['pass'] for c in checks) else 'FAIL','checks':checks,'check_count':len(checks),'independent':False,'not_proven':['Economic winner','Real dispatch or crew feasibility','Accepted future physical inventory','P05 demand or willingness to pay','P06 independent acceptance']}
(ROOT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
if not all(c['pass'] for c in checks):
 print(json.dumps([c for c in checks if not c['pass']],ensure_ascii=False));raise SystemExit(1)
files=[]
for f in sorted(ROOT.rglob('*')):
 if f.is_file() and f.name!='output_manifest.json' and '__pycache__' not in f.parts and not f.name.endswith('.pyc'):
  b=f.read_bytes();files.append({'path':str(f.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'role':'source' if 'live' in f.relative_to(ROOT).parts else 'reproduction' if f.suffix=='.py' else 'output'})
manifest={'package':'GOJ/research_v1','stage':'A','status':result['status'],'as_of':'2026-11-12','write_root':str(ROOT),'source_pin_file':'source_pins.json','source_pin_file_sha256':hashlib.sha256((ROOT/'source_pins.json').read_bytes()).hexdigest(),'git_commit_operations':'NONE','files':files,'file_count':len(files),'total_bytes':sum(x['bytes'] for x in files),'self_hash_policy':'output_manifest excludes itself; coordinator records its hash; no full dependency copies','validation_boundary':'Integrity/lineage/design calendar only; not independent economic acceptance'}
(ROOT/'output_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'checks':len(checks),'files':len(files),'bytes':manifest['total_bytes'],'manifest_sha256':hashlib.sha256((ROOT/'output_manifest.json').read_bytes()).hexdigest()},ensure_ascii=False))
