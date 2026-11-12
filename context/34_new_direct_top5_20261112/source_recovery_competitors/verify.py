import csv,json,sys,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
errors=[]
def check(ok,msg):
 if not ok: errors.append(msg)
required={
 'classification.csv':['pair','ordinary_class','target_class','rw_status','competitor_source_ids','rw_source_ids'],
 'schedules.csv':['schedule_id','pair','origin','destination','week','source_id','direct_source_field','count_source_field','count_published_pattern'],
 'fares_and_alternatives.csv':['pair','origin','destination','week','gross_rub','quote_source_id','direct_source_field'],
 'demand_reasons.csv':['pair','origin','destination','ordinary_endpoint_journeys','target_endpoint_journeys','demand_source_id','direct_source_field'],
 'sources.csv':['source_id','url','publication_date','retrieved_at','covered_dates','locator','short_quote','proves','excerpt_file']}
rows={}; widths={}
for name,cols in required.items():
 try:
  with (P/name).open(newline='',encoding='utf-8') as f: table=list(csv.reader(f))
  check(bool(table),'empty '+name)
  head=table[0];check(len(head)==len(set(head)),'duplicate columns '+name)
  check(set(cols)<=set(head),'schema '+name)
  check(all(len(r)==len(head) for r in table[1:]),'width '+name)
  rows[name]=[dict(zip(head,r)) for r in table[1:]]
  widths[name]={'columns':len(head),'rows':len(table)-1}
 except Exception as e: errors.append(name+': '+repr(e))
try:
 sources={r['source_id']:r for r in rows['sources.csv']}
 check(len(sources)==len(rows['sources.csv']),'duplicate source ids')
 for sid,r in sources.items():
  check((P/r['excerpt_file']).is_file(),'missing excerpt '+sid)
  check(all(r[x] for x in ['url','publication_date','retrieved_at','covered_dates','locator','short_quote','proves']),'source metadata '+sid)
 for filename,table in rows.items():
  for i,r in enumerate(table):
   for key,value in r.items():
    if key.endswith('source_id') or key.endswith('source_ids'):
     for sid in value.split(';'):
      check(sid=='UNKNOWN' or sid in sources,f'broken reference {filename}:{i}:{sid}')
 pairs={'TJM-MRV','CEK-MRV','SVX-KJA','SVX-IKT','SVX-VVO','SVX-KHV'}
 check(len(rows['classification.csv'])==6,'classification row count')
 check({r['pair'] for r in rows['classification.csv']}==pairs,'assigned pairs')
 for name in ['schedules.csv','fares_and_alternatives.csv','demand_reasons.csv']:
  for pair in pairs:
   a,b=pair.split('-')
   subset=[r for r in rows[name] if r['pair']==pair]
   check({(r['origin'],r['destination']) for r in subset}=={(a,b),(b,a)},'directions '+name+pair)
   if name!='demand_reasons.csv':
    for o,d in [(a,b),(b,a)]:
     check({r['week'] for r in subset if r['origin']==o and r['destination']==d}=={'ordinary','target'},'week coverage '+name+pair+o)
 from datetime import date,timedelta
 patterns=[r for r in rows['schedules.csv'] if r['count_published_pattern']!='UNKNOWN']
 for r in patterns:
  check(bool(r['direct_source_field']) and r['count_source_field']!='UNKNOWN','numeric source '+r['schedule_id'])
  dates=r['applicable_departures'].split(';')
  check(len(set(dates))==int(r['count_published_pattern']),'count '+r['schedule_id'])
  for dt in dates:
   check(r['valid_start']<=dt<=r['valid_end'] and r['week_start']<=dt<=r['week_end'],'date scope '+r['schedule_id'])
   check(date.fromisoformat(dt).weekday() in map(int,r['days'].split(',')),'weekday '+r['schedule_id'])
 check(all(r['gross_rub']=='UNKNOWN' for r in rows['fares_and_alternatives.csv']),'unbacked quote')
 check(all(r['ordinary_endpoint_journeys']=='UNKNOWN' and r['target_endpoint_journeys']=='UNKNOWN' for r in rows['demand_reasons.csv']),'unbacked demand')
 req=json.loads((P/'actual_requests.json').read_text())
 actual=sum(len(r['args'].get('search_query',[])) for r in req['requests'])
 check(actual==10 and actual<=10,'search budget')
 urls={p['ref_id'] for r in req['requests'] for p in r['args'].get('open',[]) if p['ref_id'].startswith('http')}
 check(len(urls)==16,'unique opened page count')
 check(all('response' in r and r['response'] for r in req['requests']),'missing actual response')
 check((P/'notes.md').is_file(),'notes missing')
except Exception as e: errors.append('validation exception: '+repr(e))
result={'status':'PASS_STRUCTURAL_AND_REFERENCE_CHECKS' if not errors else 'FAIL','research_complete_one_pass':not errors,'market_coverage_complete':False,'errors':errors,'tables':widths,'search_queries':10,'unique_page_open_attempts':16,'claims':'Published patterns only; no verified RW absence, comparable fares, or directed OD. No blanket VERIFIED status.','sha256':{n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in required if (P/n).exists()}}
(P/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
sys.exit(bool(errors))

