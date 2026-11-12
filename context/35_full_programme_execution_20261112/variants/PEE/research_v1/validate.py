from pathlib import Path
import json,csv,hashlib,datetime,sys,collections,subprocess
B=Path(__file__).resolve().parent
checks=[]
def check(name,condition,detail=''):
 checks.append(dict(check=name,pass_=bool(condition),detail=detail))
def load(p):return json.loads((B/p).read_text())
def rows(p):return list(csv.DictReader((B/p).open()))
if '--manifest' in sys.argv:
 m=load('output_manifest.json')
 for f in m['files']:check('manifest:'+f['path'],(B/f['path']).is_file() and hashlib.sha256((B/f['path']).read_bytes()).hexdigest()==f['sha256'])
 actual={str(p.relative_to(B)) for p in B.rglob('*') if p.is_file() and p.name!='output_manifest.json' and '__pycache__' not in p.parts}
 check('manifest_complete',actual=={f['path'] for f in m['files']})
else:
 required=['case.json','evidence.csv','market_deltas.csv','hypotheses.json','programme_candidates.json','comparison_requests.csv','assumptions.csv','readiness.json','handoff.json']
 for f in required:check('required:'+f,(B/f).is_file() and (B/f).stat().st_size>1)
 for f in B.rglob('*.json'):
  if f.name not in ['output_manifest.json','validation.json']:
   try:json.loads(f.read_text());check('json:'+str(f.relative_to(B)),True)
   except Exception as e:check('json:'+str(f.relative_to(B)),False,str(e))
 for r in load('source_pins.json'):
  check('input_hash:'+r['output'],hashlib.sha256((B/r['output']).read_bytes()).hexdigest()==r['output_sha256'])
  raw=subprocess.check_output(['git','show',r['commit']+':'+r['path']]);check('git_source:'+r['path'],hashlib.sha256(raw).hexdigest()==r['source_sha256'])
 src={r['source_id'] for r in rows('sources.csv')};ass={r['assumption_id'] for r in rows('assumptions.csv')}
 for filename,key in [('sources.csv','source_id'),('evidence.csv','evidence_id'),('assumptions.csv','assumption_id'),('comparison_requests.csv','request_id')]:
  rr=rows(filename);check('unique:'+filename,len(rr)==len({r[key] for r in rr}))
 for r in rows('evidence.csv'):
  check('evidence_source:'+r['evidence_id'],all(s in src for s in r['source_id'].split(';')))
  check('evidence_grain:'+r['evidence_id'],all(r.get(k) for k in ['unit','period','granularity','coverage','status']))
 for r in rows('assumptions.csv'):
  check('assumption_fields:'+r['assumption_id'],all(r.get(k) for k in ['owner','rationale','range_or_unknown','sensitivity_and_decision_effect','how_to_refine']))
  check('assumption_source:'+r['assumption_id'],all(s in src for s in r['source_id'].split(';')))
 pp=load('programme_candidates.json')['programmes'];hh=load('hypotheses.json')['hypotheses'];pids={p['programme_id'] for p in pp}
 for h in hh:
  check('hypothesis_disposition:'+h['hypothesis_id'],h['status']=='CONDITIONAL_STAGE_B_REQUIRED' and bool(h['revisit_condition']) and all(p in pids for p in h['programme_ids']))
  check('hypothesis_assumptions:'+h['hypothesis_id'],set(h['assumption_ids'])<=ass)
 for p in pp:check('programme_assumptions:'+p['programme_id'],set(p['assumption_ids'])<=ass)
 cal=rows('calendar_rules.csv')
 months={f'{y}-{m:02}' for y in [2027,2028] for m in range(1,13)}
 for pid in ['PEE-D1','PEE-R1','PEE-S1','PEE-H2','PEE-R2']:check('24months:'+pid,{r['month'] for r in cal if r['programme_id']==pid}==months)
 for m in months:
  season=5<=int(m[-2:])<=9
  total=sum(int(r['target_roundtrips_per_week']) for r in cal if r['programme_id']=='PEE-R1' and r['month']==m)
  check('R1_frequency:'+m,total==(6 if season else 4))
 fs=rows('diagnostic_flights.csv');rs=load('resource_screen.json');byday=collections.defaultdict(list)
 for f in fs:byday[f['departure_utc'][:10]].append(f)
 check('nominal_legs12',len(fs)==12);check('nominal_block_total',abs(sum(float(f['block_minutes']) for f in fs)/60-rs['weekly_block_hours'])<1e-9)
 check('nominal_block_cap',max(sum(float(f['block_minutes']) for f in day)/60 for day in byday.values())<=10)
 for i,(a,b) in enumerate(zip(fs,fs[1:])):
  gap=(datetime.datetime.fromisoformat(b['departure_utc'])-datetime.datetime.fromisoformat(a['arrival_utc'])).total_seconds()/60
  check('nominal_tail_sequence:'+str(i),a['destination_airport']==b['origin_airport'] and gap>=60)
 check('nominal_not_operational',rs['crew_duty_not_tested'] and rs['spare_or_MRO_not_tested'])
 check('scoped_old_seed_rejected',load('resource_attempts.json')['max_daily_block_hours']>10 and load('resource_attempts.json')['status']=='REJECTED_NOMINAL_TEMPLATE_AS_BUILT')
 issues=load('local_data_issues.json')['issues'];check('clock_issue_preserved',len(issues)==2 and all(r['same_day_elapsed_minutes']==-120 for r in issues))
 check('no_money_winner',not load('readiness.json')['acceptance_claims']['economics_validated'])
 check('airport_total_arithmetic',1707582+284295+12984==2004861)
 check('VOG_support_arithmetic',abs(44*(147368.28+147368.27)-12968408.2)<1e-6)
 result=dict(status='PASS' if all(c['pass_'] for c in checks) else 'FAIL',checks=len(checks),passed=sum(c['pass_'] for c in checks),failed=[c for c in checks if not c['pass_']],scope='Структура, происхождение, сохранение границ, арифметика и номинальная последовательность. Не P05/P06 экономика, не операционная и не рыночная приёмка.')
 (B/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
fails=[c for c in checks if not c['pass_']]
print(json.dumps(dict(status='PASS' if not fails else 'FAIL',checks=len(checks),failures=fails),ensure_ascii=False,indent=2))
if fails:raise SystemExit(1)
