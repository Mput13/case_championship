#!/usr/bin/env python3
"""Offline rebuild from exact git blobs + small local HTTP bodies. Writes only own scope."""
import collections,csv,datetime,hashlib,io,itertools,json,pathlib,re,subprocess
from lxml import html
R=pathlib.Path(__file__).resolve().parent
TS='93fa5cf4a10ab67e05c93d19fc5375fc58ef9299';CORE='505e24663e5952bae9b9540bb9a5a622663bfc2a';STAGE='6ec84a7d2a6eb50b547a61df82fc5a424f48f146';NASTYA='2f03b693a62c219e9475fcd1e26295039f6a49d7'
PREF='context/16_agent_research/core/branches/operating_evidence/'
LOCK=[]
def blob(sha,path,grain,author_ref):
 data=subprocess.check_output(['git','show',sha+':'+path]);meta=subprocess.check_output(['git','show','-s','--format=%H%n%an%n%aI',sha],text=True).splitlines();LOCK.append(dict(source_commit=meta[0],path=path,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),grain=grain,git_author=meta[1],authored_at=meta[2],author_ref=author_ref));return data

def rows(sha,path,grain,author):return list(csv.DictReader(io.StringIO(blob(sha,path,grain,author).decode('utf-8-sig'))))
def writecsv(name,rr,fields=None):
 if not fields:fields=list(dict.fromkeys(k for r in rr for k in r))
 with (R/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rr)

def js(name,obj):(R/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def txt(el):return ' '.join(el.text_content().split())
refs=rows(TS,'context/21_team_proposals/routes.csv','candidate × physical pair','Цири / mput')
services=rows(TS,'context/17_aircraft_route_review/evidence/published_service_facts.csv','published dated directional service','Цири / mput')
comp=rows(TS,'context/12_network_economics/competition.csv','week × directed route × snapshot','Цири / mput')
old_sources=json.loads(blob(TS,'context/12_network_economics/sources.json','public source receipts','Цири / mput'))
omsp=rows(CORE,PREF+'normalized/omsk_outbound_week_20261207.csv','OMS dated outbound physical next leg','core / Mput13 with operating-evidence agent authorship retained')
omsrules=rows(CORE,PREF+'normalized/omsk_domestic_timetable_rows.csv','airport paired/through service rule','core / Mput13 with operating-evidence agent authorship retained')
coremanifest=json.loads(blob(CORE,PREF+'dataset_manifest.json','source × receipt','core / Mput13 with operating-evidence agent authorship retained'))
stage=rows(STAGE,'context/22_stage1_audit/accepted_research.csv','airport × criterion × scoped evidence','stage22 / mput; original source not inferred from Git author')
blob(STAGE,'context/22_stage1_audit/main_source_checks.md','primary-source check note','stage22 / mput')
for f in ['airport_tech.csv','competitor_hubs.csv','pax_2025_overrides.csv']:
 blob(NASTYA,'data/manual/'+f,'airport × criterion','Анастасия / kiruha355')
# Scope/network keys follow final contributor proposal, not an earlier sensitivity selection.
market=collections.defaultdict(set);roles=collections.defaultdict(set)
for x in refs:
 if x['network'] not in ['D_SVX8','H_UFA_4','H_UFA_8']:continue
 a,b=x['pair'].split('-')
 for o,d in [(a,b),(b,a)]:market[o,d].add(x['network']);roles[o,d].add('DIRECT_PROGRAM' if x['network']=='D_SVX8' else 'HUB_RAY')
leaves={n:sorted(set(c for r in refs if r['network']==n for c in r['pair'].split('-') if c!='UFA')) for n in ['H_UFA_4','H_UFA_8']}
for n,ll in leaves.items():
 for o,d in itertools.permutations(ll,2):market[o,d].add(n);roles[o,d].add('ENDPOINT_OD_VIA_UFA')
js('candidate_scope.json',dict(source_commit=TS,path='context/21_team_proposals/routes.csv',leaves=leaves,scope='AUTHOR_PROPOSAL; all leaf pairs are coverage denominator, not proof they are sold or selected by a dated connection algorithm',warning='H_UFA_4 in earlier selected_networks RELAXED_SAME_INPUTS_100 has GOJ instead of MRV. That is a distinct variant; do not silently merge.'))
receipts=json.loads((R/'http_receipts.json').read_text());recmap={r['source_id']:r for r in receipts}
# Retain source rule facts. Range is inclusive; single date is not daily recurrence.
rules=[];dated=[]
for sid,code in [('ufa_oms','OMS'),('ufa_njc','NJC'),('ufa_mrv','MRV'),('ufa_kuf','KUF'),('ufa_goj_fixed','GOJ')]:
 for key,di in [(sid,'FROM'),(sid+'_to' if sid!='ufa_goj_fixed' else 'ufa_goj_to','TO')]:
  rec=recmap.get(key)
  if not rec or rec['status']!='ACQUIRED':continue
  doc=html.fromstring((R/rec['raw_local_path']).read_bytes().decode('utf-8'))
  direction=doc.xpath('//input[@name="DIRECTION"]/@value');assert direction==[di],(key,direction,di)
  for idx,card in enumerate(doc.xpath('//div[@class="b-card-sez-card"]'),1):
   def v(cl):return [txt(e) for e in card.xpath('.//div[contains(concat(" ",normalize-space(@class)," ")," b-card-sez-card__td_'+cl+' ")]//span[contains(concat(" ",normalize-space(@class)," ")," b-card-sez-card__info ")]')]
   def one(cl):
    vs=v(cl);return vs[0] if vs else ''
   period=v('period');days=card.xpath('.//span[contains(concat(" ",normalize-space(@class)," ")," _active ")]/text()')
   if len(period) not in [1,2]:raise ValueError((key,idx,period))
   dates=[datetime.datetime.strptime(s,'%d.%m.%Y').date() for s in period]
   o,d=(code,'UFA') if di=='FROM' else ('UFA',code)
   rr=dict(source_id=key,source_card=idx,source_rule_csv_row=len(rules)+2,origin=o,destination=d,source_direction=di,carrier=one('company'),flight=one('number'),departure_local=one('time--start'),arrival_local=one('time--end'),displayed_duration=one('duration'),aircraft=one('flight'),active_days=';'.join(days),period_start=dates[0].isoformat(),period_end=dates[-1].isoformat(),period_kind='SINGLE_DATE' if len(dates)==1 else 'INCLUSIVE_RANGE',html_sha256=rec['sha256'],source_url=rec['url'],evidence_kind='PUBLISHED_AIRPORT_DIRECT_LIST_NOT_EXECUTED',nonstop_status='ADVERTISED_DIRECT_LIST; stops not independently validated',seats='',commercial_access='UNKNOWN; timetable can contain charter/single-date services')
   rules.append(rr)
   for dt in [datetime.date(2026,12,7)+datetime.timedelta(days=i) for i in range(7)]:
    if dates[0]<=dt<=dates[-1] and (len(dates)==1 or ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'][dt.weekday()] in days):dated.append(dict(rr,date=dt.isoformat()))
writecsv('ufa_schedule_rules.csv',rules)
writecsv('ufa_dated_services.csv',dated,list(rules[0])+['date'])
# Source-specific dated evidence is retained; do not sum two endpoint publications as separate flights.
evidence=[]
for i,r in enumerate(services,2):
 if (r['origin'],r['destination']) not in market:continue
 evidence.append(dict(origin=r['origin'],destination=r['destination'],date=r['date'],departure_local=r['departure_local'],arrival_local=r['arrival_local'],carrier=r['carrier'],flight=r['flight'],aircraft=r['aircraft'],duration_minutes=r['block_minutes'],duration_status='AUTHOR_EXTRACTED_FROM_PUBLISHED_SCHEDULE',source_id=r['source'],source_url=r['source_url'],html_sha256=r['html_sha256'],source_commit=TS,source_path='context/17_aircraft_route_review/evidence/published_service_facts.csv',source_row=i,collector='Цири / mput',nonstop_status='PUBLISHED_AIRPORT_SERVICE; no execution proof',period=r['period'],evidence_kind=r['evidence_kind']))
omsreceipt=next(x for x in coremanifest if x['dataset_id']=='omsk_winter_2026')
omrules={r['source_text_line']:r for r in omsrules}
for i,r in enumerate(omsp,2):
 o,d=r['origin_airport_iata'],r['destination_airport_iata']
 if (o,d) not in market:continue
 rule=omrules[r['source_text_line']]
 evidence.append(dict(origin=o,destination=d,date=r['departure_date_local'],departure_local=r['departure_local'][11:16],arrival_local=r['published_onward_arrival_local_raw'].replace('.',':'),carrier=r['carrier_raw'],flight=r['outbound_flight_numeric'],aircraft=rule['aircraft_type_raw'],duration_minutes='',duration_status='UNKNOWN; source arrival date not inferred',source_id='omsk_winter_2026',source_url=omsreceipt['source_url'],html_sha256=omsreceipt['sha256'],source_commit=CORE,source_path=PREF+'normalized/omsk_outbound_week_20261207.csv',source_row=i,collector='core / Mput13; reused operating-evidence extraction',nonstop_status=r['nonstop_status'],period=rule['period_raw'],evidence_kind='REUSED_PRIMARY_PLANNED_NEXT_LEG_NOT_ACTUAL'))
for r in dated:
 dur=r['displayed_duration'].split(':');mins=int(dur[0])*60+int(dur[1]) if len(dur)==2 else ''
 evidence.append(dict(origin=r['origin'],destination=r['destination'],date=r['date'],departure_local=r['departure_local'],arrival_local=r['arrival_local'],carrier=r['carrier'],flight=r['flight'],aircraft=r['aircraft'],duration_minutes=mins,duration_status='SOURCE_DISPLAYED; clock checks separate',source_id=r['source_id'],source_url=r['source_url'],html_sha256=r['html_sha256'],source_commit='',source_path='ufa_schedule_rules.csv',source_row=r['source_rule_csv_row'],collector='night primary-evidence / Sol 6.1 xhigh',nonstop_status=r['nonstop_status'],period=r['period_start']+'/'+r['period_end'],evidence_kind=r['evidence_kind']))
# Additional endpoint schedules, raw periods omit year: assignment is explicit and scenario-season qualified.
months={'янв':1,'фев':2,'мар':3,'апр':4,'май':5,'мая':5,'июн':6,'июл':7,'авг':8,'сен':9,'окт':10,'ноя':11,'дек':12}
wd={'пн':0,'вт':1,'ср':2,'чт':3,'пт':4,'сб':5,'вс':6};tz={'SVX':5,'AER':3,'KJA':7,'KUF':4,'KZN':3,'MRV':3,'OMS':6,'REN':5,'VOG':3,'GOJ':3,'UFA':5,'ARH':3,'GSV':4,'NJC':5}
additional_rules=[]
for sid,airport,arrival in [('kuf_schedule_new','KUF',False),('kuf_schedule_arr_new','KUF',True),('gsv_schedule_new','GSV',False),('gsv_schedule_arr_new','GSV',True)]:
 rec=recmap.get(sid)
 if not rec or rec['status']!='ACQUIRED':continue
 doc=html.fromstring((R/rec['raw_local_path']).read_bytes().decode('utf-8'))
 for idx,tr in enumerate(doc.xpath('//tr'),1):
  vals=[txt(c) for c in tr.xpath('./td|./th')]
  if len(vals)!=8 or not re.match(r'^\d\d:\d\d',vals[0]):continue
  dep,arr,days,period,carrier,flight,aircraft,other=vals
  o,d=(other,airport) if arrival else (airport,other)
  if (o,d) not in market:continue
  pp=re.findall(r'(\d+)\s+([а-я]+)',period.lower())
  if len(pp)!=2:raise ValueError((sid,idx,period))
  dm=[(int(x),months[y[:3]]) for x,y in pp]
  lo=datetime.date(2026 if dm[0][1]>=10 else 2027,dm[0][1],dm[0][0]); hi=datetime.date(lo.year+(dm[1][1]<lo.month),dm[1][1],dm[1][0])
  active=list(range(7)) if 'ежеднев' in days else [wd[x.strip()] for x in days.split(',') if x.strip() in wd]
  rule=dict(source_id=sid,source_row=idx,origin=o,destination=d,departure_local=dep,arrival_local=arr,weekdays=days,period_raw=period,assigned_period_start=lo.isoformat(),assigned_period_end=hi.isoformat(),year_basis='INFERRED_WINTER_2026_27; source rule omits year',carrier=carrier,flight=flight,aircraft=aircraft,html_sha256=rec['sha256'],source_url=rec['url'])
  additional_rules.append(rule)
  clock=lambda x:int(x[:2])*60+int(x[3:5]);duration=(clock(arr)-tz[d]*60-clock(dep)+tz[o]*60)%1440
  for i in range(7):
   dt=datetime.date(2026,12,7)+datetime.timedelta(days=i)
   if lo<=dt<=hi and dt.weekday() in active:
    evidence.append(dict(origin=o,destination=d,date=dt.isoformat(),departure_local=dep,arrival_local=arr,carrier=carrier,flight=flight,aircraft=aircraft,duration_minutes=duration,duration_status='DERIVED_CLOCK_DIFFERENCE; year seasonal inference, local clocks as published',source_id=sid,source_url=rec['url'],html_sha256=rec['sha256'],source_commit='',source_path='endpoint_schedule_rules.csv',source_row=len(additional_rules)+1,collector='night primary-evidence / Sol 6.1 xhigh',nonstop_status='PUBLISHED_AIRPORT_DIRECT_SERVICE; stops not independently checked',period=period+'; assigned '+lo.isoformat()+'/'+hi.isoformat(),evidence_kind='PUBLISHED_PLAN_YEAR_ASSIGNED_NOT_EXECUTED'))
writecsv('endpoint_schedule_rules.csv',additional_rules)
# Resolve inherited raw hashes from the exact earlier receipt, without calling it a new acquisition.
oldmap={x['id']:x for x in old_sources}
for e in evidence:
 if not e['html_sha256'] and e['source_id'] in oldmap:e['html_sha256']=oldmap[e['source_id']]['sha256']

writecsv('dated_evidence.csv',evidence)
# Cards keep each source distinct. Duplicates are not additive network capacity.
cards=[];groups=collections.defaultdict(list)
for e in evidence:groups[e['origin'],e['destination'],e['carrier'],e['flight'],e['source_id']].append(e)
for (o,d,c,f,sid),ee in sorted(groups.items()):
 unique={(x['date'],x['departure_local']):x for x in ee}
 ds=sorted({x['date'] for x in ee}); durations=sorted({int(x['duration_minutes']) for x in ee if str(x['duration_minutes']).isdigit()})
 new=sid.startswith('ufa_');rw=('RED WINGS' in c.upper() or 'РедВингс' in c or c=='Red Wings')
 cards.append(dict(card_id='RPC'+str(len(cards)+1).zfill(3),candidate_ids=';'.join(sorted(market[o,d])),market_roles=';'.join(sorted(roles[o,d])),origin=o,destination=d,market_unit='directed endpoint journey; no passenger quantity observed',period_start='2026-12-07',period_end='2026-12-13',product_type='AIR_PUBLISHED_SERVICE',nonstop_status=';'.join(sorted({x['nonstop_status'] for x in ee})),operating_marketing_status='SOURCE_CARRIER_LABEL; codeshare scope not independently assumed',via_airports='',input_set_id='src_'+hashlib.sha256((sid+'|'+ee[0]['html_sha256']).encode()).hexdigest()[:16],carrier=c,flight=f,own_RW=str(rw).lower(),one_way_departures=len(unique),frequency_unit='published departures in this one direction during 7-day period',departure_dates=';'.join(ds),departure_local=';'.join(sorted({x['departure_local'] for x in ee})),arrival_local=';'.join(sorted({x['arrival_local'] for x in ee})),duration_min_minutes=min(durations) if durations else '',duration_max_minutes=max(durations) if durations else '',duration_status=ee[0]['duration_status'],aircraft=';'.join(sorted({x['aircraft'] for x in ee})),seats_per_departure='',seats_status='UNKNOWN_CONFIGURATION',comparable_fare_rub='',fare_status='NO_SAME_DATE_FINAL_20KG_QUOTE',currency='RUB',price_basis='UNKNOWN',tax_basis='UNKNOWN',source_ids=sid,source_urls=ee[0]['source_url'],source_commit=ee[0]['source_commit'],source_path=ee[0]['source_path'],source_rows=';'.join(str(x['source_row']) for x in ee),raw_sha256=ee[0]['html_sha256'],author_ref=ee[0]['collector'],value_status='PUBLISHED_PLAN_YEAR_ASSIGNED_NOT_SALES' if any('YEAR_ASSIGNED' in x['evidence_kind'] for x in ee) else 'PUBLISHED_PLAN_NOT_SALES',acceptance_scope='EXTRACTION_CHECKED;JOIN_CHECKED',coverage_limit='source-specific offers, not complete market; duplicate publications must not be added',period_2019='NOT_IN_SCOPE',period_2025='NOT_SAME_PERIOD',period_2027='NO_AUTOMATIC_EXTENSION',network_implication='own RW migration must be separated' if rw else 'substitute for endpoint journey; capture and demand UNKNOWN'))
for (o,d) in sorted(market):
 if any(c['origin']==o and c['destination']==d for c in cards):continue
 cards.append(dict(card_id='RPC'+str(len(cards)+1).zfill(3),candidate_ids=';'.join(sorted(market[o,d])),market_roles=';'.join(sorted(roles[o,d])),origin=o,destination=d,market_unit='directed endpoint journey; no passenger quantity observed',period_start='2026-12-07',period_end='2026-12-13',product_type='NO_MATCHED_PRODUCT',nonstop_status='UNKNOWN',operating_marketing_status='UNKNOWN',via_airports='',input_set_id='night_primary_coverage_20261110',carrier='',flight='',own_RW='',one_way_departures='',frequency_unit='UNKNOWN; not zero',departure_dates='',departure_local='',arrival_local='',duration_min_minutes='',duration_max_minutes='',duration_status='UNKNOWN',aircraft='',seats_per_departure='',seats_status='UNKNOWN',comparable_fare_rub='',fare_status='NO_SAME_DATE_FINAL_20KG_QUOTE',currency='RUB',price_basis='UNKNOWN',tax_basis='UNKNOWN',source_ids='',source_urls='',source_commit='',source_path='',source_rows='',raw_sha256='',author_ref='night primary-evidence / Sol 6.1 xhigh',value_status='UNKNOWN',acceptance_scope='COVERAGE_ONLY',coverage_limit='No matched target-week row in finite inputs; not proof of no service',period_2019='NOT_IN_SCOPE',period_2025='NOT_SAME_PERIOD',period_2027='UNKNOWN',network_implication='do not set competition or yield to zero; check direct, through, connecting and ground products'))
writecsv('route_product_cards.csv',cards)
coverage=[]
for (o,d),nets in sorted(market.items()):
 cc=[x for x in cards if x['origin']==o and x['destination']==d and x['product_type']=='AIR_PUBLISHED_SERVICE']
 old=[x for x in comp if x['week']=='2026-12-07' and (x['origin'],x['destination'])==(o,d)]
 coverage.append(dict(origin=o,destination=d,candidate_ids=';'.join(sorted(nets)),market_roles=';'.join(sorted(roles[o,d])),period_start='2026-12-07',period_end='2026-12-13',positive_source_cards=len(cc),dated_evidence_status='POSITIVE_PUBLISHED_ROWS' if cc else 'UNKNOWN_NO_MATCHED_POSITIVE_ROW',old_competition_status=';'.join(sorted({x['status'] for x in old})) or 'NOT_COVERED',source_ids=';'.join(sorted({x['source_ids'] for x in cc})),nonadditive_publication_duplicates='OMS-SVX' if (o,d)==('OMS','SVX') else '',seats='UNKNOWN',same_date_fare='UNKNOWN',endpoint_OD_quantity='UNKNOWN',through_stop_check='PARTIAL',connecting_product='UNKNOWN; no dated leg/MCT/through-ticket join',ground_product='HISTORICAL_PRIMARY_RAIL_CARD; Dec validity UNKNOWN' if {o,d}=={'KUF','UFA'} else 'NOT_CHECKED',summer_2027='UNKNOWN'))
writecsv('coverage.csv',coverage)
mapping=[]
for c in cards:
 for candidate in c['candidate_ids'].split(';'):
  mapping.append(dict(model_id='tsiri_proposal_evidence_adapter',author_ref='Цири / mput; AUTHOR_PROPOSAL',source_commit=TS,program_path='context/21_team_proposals/routes.csv',input_set_id=c['input_set_id'],run_id='night_primary_20261110',scenario_id='published_plan_20261207_13_evidence_only',candidate_id=candidate,card_id=c['card_id'],origin=c['origin'],destination=c['destination'],period_start=c['period_start'],period_end=c['period_end'],direction_scope='ONE_DIRECTION',market_unit='directed endpoint journey; no measured demand',currency='RUB',price_basis='UNKNOWN',tax_basis='UNKNOWN',value_status=c['value_status'],acceptance_scope=c['acceptance_scope'],evidence_source_commit=c['source_commit'],evidence_author_ref=c['author_ref'],numerical_comparison_scope='supply evidence only; no demand/economics/rating acceptance'))
writecsv('adapter_mapping.csv',mapping)

# Narrow evidence reuse: preserve original source receipts and parent acquisitions with explicit attribution.
js('core_omsk_receipt.json',omsreceipt)
parent=pathlib.Path('/Users/a/agent-audit-2026-09/case_championship/context/22_case_alignment_20261110')
parents=[]
for name in ([] if (R/'parent_context_lock.json').exists() else ['coverage_review.md','primary_manifest.json']):
 b=(parent/name).read_bytes();parents.append(dict(workspace_path=str(parent/name),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),source_commit=None,source_commit_reason='parent workspace context not tracked at read HEAD; bytes pinned separately',parent_head_at_read=subprocess.check_output(['git','-C',str(parent),'rev-parse','HEAD'],text=True).strip(),author_ref='coordinator / Mput13; reused not new collection'))
if parents:js('parent_context_lock.json',parents)
if not (R/'parent_primary_receipts.json').exists():js('parent_primary_receipts.json',dict(source='parent context22/primary_manifest.json',reuse=True,acquisitions=json.loads((parent/'primary_manifest.json').read_text())['acquisitions']))
js('source_lock.json',LOCK)
js('old_schedule_sources.json',old_sources)
print(json.dumps(dict(ufa_rules=len(rules),ufa_targetweek_rows=len(dated),dated_evidence=len(evidence),cards=len(cards),directed_markets=len(coverage),positive_directed_markets=sum(bool(x['positive_source_cards']) for x in coverage)),ensure_ascii=False))
