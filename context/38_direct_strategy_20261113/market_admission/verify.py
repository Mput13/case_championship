import csv,json,hashlib,datetime,re
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2]
def read(n):return list(csv.DictReader((P/n).open()))
checks={};errors=[]
def check(k,c):
 checks[k]=bool(c)
 if not c:errors.append(k)
files=['canonical_pairs.csv','canonical_services.csv','canonical_fares.csv','alternatives.csv','monthly_evidence.csv','source_admission.csv','sources.csv','decision_gaps.csv']
for name in files:
 with (P/name).open() as f:
  rows=list(csv.reader(f));check('width_'+name,all(len(x)==len(rows[0]) for x in rows))
sources=read('sources.csv');ids={x['source_id'] for x in sources};check('source_keys',len(ids)==len(sources));svc=read('canonical_services.csv');pairs=read('canonical_pairs.csv');seed=list(csv.DictReader((P.parent/'pair_seed.csv').open()));check('exact_seed25',len(pairs)==25 and {x['pair'] for x in pairs}=={x['pair'] for x in seed});check('seed_columns_preserved',all(all(x[k]==next(s for s in seed if s['pair']==x['pair'])[k] for k in seed[0]) for x in pairs));check('service_key',len({x['service_id'] for x in svc})==len(svc))
for name in files:
 if name=='sources.csv':continue
 check('refs_'+name,all(all(k in ids for k in x['source_id'].split(';')) for x in read(name)))
check('positive_only',all(x['flight'] not in ['', 'UNKNOWN'] and x['status']!='UNKNOWN' for x in svc));check('service_periods',all(x['valid_start']<=x['valid_end'] and re.fullmatch(r'\d{4}-\d\d-\d\d',x['valid_start']) and re.fullmatch(r'\d{4}-\d\d-\d\d',x['valid_end']) for x in svc))
old=json.loads((P/'excerpts/old_positive_baseline.json').read_text());check('baseline_equals_completed_P36',old==list(csv.DictReader((R/'P36/market_recovery/canonical_services.csv').open())));preserved={x['service_id']:json.loads(x['old_record_json']) for x in svc if x['old_record_json']};check('all49_P36_verbatim',all(preserved.get(x['service_id'])==x for x in old));check('all46_P34_verbatim',len([x for x in old if x['service_id'].startswith('P34-')])==46 and all(preserved[x['service_id']]==x for x in old if x['service_id'].startswith('P34-')))
monthly=read('monthly_evidence.csv');od=[x for x in monthly if x['metric']=='monthly_endpoint_OD'];check('monthly_key_600',len(od)==600 and len({(x['pair'],x['direction'],x['coveredperiod']) for x in od})==600);check('unknown_not_zero',all(x['value']=='UNKNOWN' and x['admission']=='NO_UPDATE' for x in od));check('all_season_peak_fields',all(all(x['2027_'+s] for s in ['winter','spring','summer','autumn','peak']) for x in pairs));check('qualified_fares_empty_honestly',len(read('canonical_fares.csv'))==0)
# Independently reconstruct every relevant primary row as extracted, all operators and directions.
lookup={frozenset((x['airport_a'],x['airport_b'])):x['pair'] for x in seed};expected=[]
for i,hub,arr in [(1,'SVX',False),(2,'SVX',True),(4,'GOJ',False),(7,'GOJ',True)]:
 raw=json.loads((P/f'excerpts/HTTP{i}_rows.json').read_text())
 for j,x in enumerate(raw):
  if len(x)==8 and re.match(r'^\d\d:',x[0]) and frozenset((hub,x[7])) in lookup:expected.append((f'HTTP{i}-ROW{j+1}',x))
actual={x['service_id']:x for x in svc if x['source_id'].startswith('HTTP')};check('all81_relevant_primary_rows',len(expected)==81 and {k for k,x in expected}==set(actual));check('primary_raw_values',all(actual[k]['flight']==x[5] and actual[k]['carrier_operated']==x[4] and actual[k]['aircraft']==x[6] and actual[k]['raw_period']==x[3] and actual[k]['departure_local']==x[0] for k,x in expected));check('context_inferred_year_label',all(x['year_basis'].startswith('context_inferred') for x in actual.values()))
def dates(x,a,b):
 cur=datetime.date.fromisoformat(max(x['valid_start'],a));end=datetime.date.fromisoformat(min(x['valid_end'],b));out=[]
 while cur<=end:
  if str(cur.weekday()) in x['days_mon0'].split(','):out.append(cur.isoformat())
  cur+=datetime.timedelta(days=1)
 return out
counts={}
for a,b,label in [('2026-11-16','2026-11-22','nov16_22'),('2027-02-01','2027-02-07','feb1_7')]:
 for direction in ['SVX-KJA','KJA-SVX']:
  hit={d for x in actual.values() if x['direction']==direction for d in dates(x,a,b)};counts[label+'_'+direction]=sorted(hit)
check('KJA_nov7_each',all(len(v)==7 for k,v in counts.items() if k.startswith('nov')));check('KJA_feb_TueSat_each',all(v==['2027-02-02','2027-02-06'] for k,v in counts.items() if k.startswith('feb')))
logs=json.loads((P/'exact_requests.json').read_text());queries=sum(len(x['args'].get('search_query',[])) for x in logs);opens=sum(len(x['args'].get('open',[]))+(x['tool']=='python3 requests.get') for x in logs);check('budget24queries35opens',queries<=24 and opens<=35);check('exact_external_args_results',all('args' in x and 'retrieved' in x and ('error' in x or 'returned_excerpt' in x) for x in logs));check('stored_returned_response',all((P/x['response_file']).is_file() for x in logs if 'response_file' in x));check('source_excerpts',all(x['excerpt'] and (P/x['excerpt']).is_file() for x in sources))
guard=json.loads((P.parent/'protected_files.json').read_text());check('guard_exact1621',len(guard)==1621 and not any('/contract/' in k for k in guard));changed=[k for k,h in guard.items() if not (R/k).is_file() or hashlib.sha256((R/k).read_bytes()).hexdigest()!=h];check('protected1621_unchanged',not changed)
result=dict(status='PASS' if not errors else 'FAIL',checks=checks,errors=errors,counts=dict(pairs=len(pairs),service_evidence_rows=len(svc),old_P34_preserved=46,old_P36_preserved=len(old),new_primary_rows=len(actual),qualified_fares=0,external_queries=queries,external_opens=opens,protected_files=len(guard)),KJA_calendar_reconstruction=counts,protected_changed=changed,meaning='Structural, raw extraction, period and preservation checks only; not full semantic truth, flight execution, inventory or demand confirmation',research_stop=True,unsupported_numeric_model_updates=0)
(P/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(bool(errors))
