"""Offline front audit. Reviewed source functions only; no foreign main/network code runs."""
from pathlib import Path
import ast,csv,datetime,html,hashlib,io,json,re,zipfile,collections
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'raw/front'
def read(name):return list(csv.DictReader((F/name).open(encoding='utf-8-sig')))
def dump(name,x):(ROOT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2))
# Execute only previously reviewed parser body and scalar constants, not source top level/main.
src=ast.parse((F/'src/fetch_telegram.py').read_text())
nodes=[x for x in src.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['TEXT_RE','DT_RE','MSK'] for t in x.targets) or isinstance(x,ast.FunctionDef) and x.name=='parse']
ns={'re':re,'html':html,'datetime':datetime.datetime,'timezone':datetime.timezone,'timedelta':datetime.timedelta}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'reviewed_front_parser','exec'),ns)
body_rx=re.compile(r'tgme_widget_message_text\s+js-message_text[^>]*>(.*?)</div>',re.S)
raw_by_id={r['id']:r for r in read('data/raw/favt_posts.csv')}
telegram={};sample={}
for path in sorted((ROOT/'raw/primary').glob('favt_info_*.html')):
 page=path.read_text(); baseline={str(r['id']):r for r in ns['parse'](page,'favt_info')}
 for pid,body in re.findall(r'data-post="favt_info/(\d+)"(.*?)(?=data-post="|\Z)',page,re.S):
  tx=body_rx.search(body)
  if not tx:continue
  correct=html.unescape(re.sub(r'<br\s*/?>','\n',tx.group(1)));correct=re.sub('<[^>]+>','',correct).strip()
  got=baseline.get(pid,{}).get('text','')
  sample[pid]={'reply_present':'js-message_reply_text' in body,'text_differs':got!=correct}
  if pid in ['4685','4687','6503']:
   telegram[pid]={'raw_record':next(i for i,r in enumerate(read('data/raw/favt_posts.csv'),2) if r['id']==pid),'dt_msk':raw_by_id[pid]['dt_msk'],'stored_equals_current_parser':raw_by_id[pid]['text']==got,'reply_present':'js-message_reply_text' in body,'stored_text_sha256':hashlib.sha256(raw_by_id[pid]['text'].encode()).hexdigest(),'current_parser_sha256':hashlib.sha256(got.encode()).hexdigest(),'main_body_sha256':hashlib.sha256(correct.encode()).hexdigest(),'stored_or_parser_intro':bool(re.search('ВВЕДЕНЫ',got)),'main_body_lifted':bool(re.search('СНЯТЫ',correct)),'main_body_airports':re.findall('НИЖНИЙ НОВГОРОД|ТАМБОВ|ЯРОСЛАВЛЬ|САМАРА|ВНУКОВО',correct),'source_html':str(path.relative_to(ROOT))}
# Rail provenance and scaled effect, without treating absence as proof of good rail.
dests=read('data/processed/destinations.csv');gaps=[r for r in dests if r['in_ssj']=='True' and r['status']=='gap'];unknown=[r for r in gaps if r['rail_hr']=='']
by={}
for r in dests:
 i=r['from'];a=by.setdefault(i,{'gap_pairs':0,'null_rail_gap_pairs':0,'gap_pop':0,'null_rail_gap_pop':0})
 if r in gaps:a['gap_pairs']+=1;a['gap_pop']+=int(r['pop'])
 if r in unknown:a['null_rail_gap_pairs']+=1;a['null_rail_gap_pop']+=int(r['pop'])
for a in by.values():a['null_share_gap_pop']=a['null_rail_gap_pop']/a['gap_pop'] if a['gap_pop'] else None
with zipfile.ZipFile(ROOT/'raw/primary/tochno_intercity.zip') as z:
 csvname=next(n for n in z.namelist() if n.endswith('.csv'));b=z.read(csvname)
 rawdata=list(csv.DictReader(io.StringIO(b.decode('utf-8-sig')),delimiter=';'))
 rail=[r for r in rawdata if r['transport_type']=='rail']
 rail_index={(r['city_from'],r['city_to']):r for r in rail}
 source_csv={'zip_member':csvname,'uncompressed_bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'records':len(rawdata),'rail_records':len(rail),'missing_reasons':dict(collections.Counter(r['missing_reason'] for r in rail if not r['distance_hr']))}
city_of={r['iata']:r['city'] for r in read('data/processed/longlist.csv')}
nulls=[]
for d in unknown:
 rr=rail_index.get((city_of[d['from']],d['to_city']),{})
 nulls.append({'from':d['from'],'to':d['to'],'pop':int(d['pop']),'source_missing_reason':rr.get('missing_reason'),'source_distance_hr':rr.get('distance_hr'),'source_comment':rr.get('comment')})
# Same min-max formula using frozen 20-city input; separate sensitivity modifications.
weights=read('data/assumptions/longlist_weights.csv');data=read('data/processed/longlist.csv');published=read('data/processed/longlist_scores.csv')
base={}
for r in data:
 q={k:(float(r[k]) if r.get(k) and re.fullmatch(r'-?\d+(\.\d+)?',r[k]) else None) for k in [x['column'] for x in weights]}
 q['competitor_hub']=1.0 if r['iata'] in ['KJA','IKT','VVO'] else 0.0
 q['dist_bases_km']=min(float(r['dist_msk_km']),float(r['dist_ekb_km']))
 q['transfer_zone']=.5 if q['transfer_zone'] is None else q['transfer_zone'];q['rostec_link']=0 if q['rostec_link'] is None else q['rostec_link']
 base[r['iata']]=q

def scores(inp,min_dist=0):
 inp={i:r for i,r in inp.items() if r['dist_bases_km']>=min_dist};out={i:0 for i in inp}
 for w in weights:
  c=w['column'];lo=min(q[c] for q in inp.values());hi=max(q[c] for q in inp.values())
  for i,q in inp.items():
   v=(q[c]-lo)/(hi-lo) if hi!=lo else 0
   if w['direction']=='-':v=1-v
   out[i]+=float(w['weight'])*v/100
 return [{'iata':i,'score':round(s,6),'rank':k} for k,(i,s) in enumerate(sorted(out.items(),key=lambda x:-x[1]),1)]
repro=scores(base);check=max(abs(next(x['score'] for x in repro if x['iata']==r['iata'])-float(r['score'])) for r in published)
null_excluded={i:{**q,'gap_pop':q['gap_pop']-by[i]['null_rail_gap_pop']} for i,q in base.items()}
competitor_cek={i:{**q,'competitor_hub':1 if i=='CEK' else q['competitor_hub']} for i,q in base.items()}
# Method sensitivity is a scenario, not evidence that CEK is an actual fortress.
scenarios={'baseline_all':repro,'null_rail_excluded_all':scores(null_excluded),'baseline_min500':scores(base,500),'null_rail_excluded_min500':scores(null_excluded,500),'CEK_competitor_hub_1_SCENARIO':scores(competitor_cek)}
near=[r for r in dests if r['in_ssj']=='True' and r['direct']=='False' and r['rail_hr'] and 12/1.11<=float(r['rail_hr'])<=12/.89]
result={'input_sha':'71b493d0051dc3acf2a7619801e5b0eb022bddd3','produced_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'telegram':{'verified_examples':telegram,'fetched_page_sample_posts':len(sample),'sample_reply_posts':sum(x['reply_present'] for x in sample.values()),'sample_parser_body_mismatches':sum(x['text_differs'] for x in sample.values()),'sample_is_not_random':True,'full_history_corrected':False},'rail':{'destination_records':len(dests),'gap_pairs':len(gaps),'null_rail_gap_pairs':len(unknown),'by_candidate':by,'source_csv':source_csv,'null_pair_provenance':nulls,'estimated_hr_near_12_under_11pct_stress_count':len(near),'near_12_stress_is_not_confidence_interval':True},'screening':{'published_score_max_rounding_delta':check,'scenarios':scenarios},'limits':['No full-history re-download or re-ranking with corrected Telegram raw was performed.','Rail unknown exclusion only bounds coding effect; it does not establish true rail alternatives.','Competitor scenario is sensitivity, not observation.']}
dump('reproduction.json',result)
print(json.dumps({'telegram_sample':{k:result['telegram'][k] for k in ['fetched_page_sample_posts','sample_reply_posts','sample_parser_body_mismatches']},'ranking':{k:[r['iata'] for r in v[:3]] for k,v in scenarios.items()},'score_reproduction_delta':check,'near12':len(near)},ensure_ascii=False,indent=2))
