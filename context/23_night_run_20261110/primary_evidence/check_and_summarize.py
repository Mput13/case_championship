#!/usr/bin/env python3
"""Meaningful checks: calendar, direction, nulls, duplicate physical services and incompatible clocks."""
import collections,csv,datetime,hashlib,json,pathlib,re,subprocess
from lxml import html
R=pathlib.Path(__file__).resolve().parent

def read(n):return list(csv.DictReader((R/n).open()))
def write(n,rows,fields=None):
 with (R/n).open('w',newline='') as f:
  w=csv.DictWriter(f,fields or list(rows[0]));w.writeheader();w.writerows(rows)
E=read('dated_evidence.csv');C=read('route_product_cards.csv');V=read('coverage.csv');U=read('ufa_schedule_rules.csv');locks=json.loads((R/'source_lock.json').read_text())
checks=[]
def check(n,v):checks.append(dict(check=n,pass_=bool(v)));assert v,n
check('all target-week evidence has explicit date',all('2026-12-07'<=e['date']<='2026-12-13' for e in E))
check('no null to zero in uncovered market products',all(c['one_way_departures']=='' for c in C if c['product_type']=='NO_MATCHED_PRODUCT'))
check('no aircraft-type to seats inference',all(c['seats_per_departure']=='' for c in C))
check('no advertised fare to yield inference',all(c['comparable_fare_rub']=='' for c in C))
check('all positive raw receipts linked',all(re.fullmatch('[0-9a-f]{64}',e['html_sha256']) for e in E))
check('all pinned source blobs hash verified',all(hashlib.sha256(subprocess.check_output(['git','show',x['source_commit']+':'+x['path']])).hexdigest()==x['sha256'] for x in locks))
receipts=json.loads((R/'http_receipts.json').read_text());check('all local acquired bodies hash verified',all(hashlib.sha256((R/r['raw_local_path']).read_bytes()).hexdigest()==r['sha256'] for r in receipts if r['status']=='ACQUIRED'))
# Check several real calendar counterexamples, not merely roundtrip serializer tests.
check('single-date UFA service UT6111 25Dec is excluded from 7-13Dec',not any(e['flight']=='UT 6111' for e in E))
check('UFA active weekday classes are used',next(x for x in U if x['source_id']=='ufa_mrv_to' and x['flight']=='A4 6122' and x['period_start']=='2026-12-03')['active_days']=='Чт')
check('UFA FROM GOJ is inbound with flight829',any(e['origin']=='GOJ' and e['destination']=='UFA' and e['flight']=='N4 829' for e in E))
# Normalize carrier aliases by service designator. Source publications remain alternatives, never summed.
carrier={'РедВингс':'WZ','ЮТэйр':'UT','Азимут':'A4','Уральские а/л':'U6'}
def fid(e):
 raw=re.sub('[^A-Z0-9]','',e['flight'].upper())
 if raw.isdigit():return carrier.get(e['carrier'],'UNKNOWN')+'-'+raw
 # first two characters are IATA designator (including digit: A4,7R), rest is flight suffix.
 return raw[:2]+'-'+raw[2:]
groups=collections.defaultdict(list)
for i,e in enumerate(E,2):groups[(e['origin'],e['destination'],e['date'],fid(e))].append((i,e))
ident=[];conflicts=[]
for key,ee in sorted(groups.items()):
 clocks=sorted({(e['departure_local'],e['arrival_local']) for _,e in ee});ids=sorted({e['source_id'] for _,e in ee});o,d,dt,f=key
 ident.append(dict(origin=o,destination=d,date=dt,normalized_flight=f,source_rows=';'.join(str(i) for i,e in ee),source_ids=';'.join(ids),publication_rows=len(ee),deduplicated_publication_key_count=1,clock_variants=json.dumps(clocks,ensure_ascii=False),clock_status='CONFLICT_HOLD' if len(clocks)>1 else 'MATCHED_OR_SINGLE_SOURCE',market_scope='published service; commercial availability and execution UNKNOWN'))
 if len(clocks)>1:conflicts.append(ident[-1])
write('service_identity.csv',ident)
write('schedule_conflicts.csv',conflicts,list(ident[0]))
for c in C:
 matches=[x for x in ident if x['origin']==c['origin'] and x['destination']==c['destination'] and c['source_ids'] in x['source_ids'].split(';') and x['normalized_flight']==fid(dict(flight=c['flight'],carrier=c['carrier']))]
 c['clock_consensus_status']='CONFLICT_HOLD' if any(x['clock_status']=='CONFLICT_HOLD' for x in matches) else 'MATCHED_OR_SINGLE_SOURCE' if matches else 'UNKNOWN'
 c['duration_usable_for_network']='false' if c['clock_consensus_status'] in ['CONFLICT_HOLD','UNKNOWN'] else 'source-specific scenario only; verify stop status and year basis'
 c['capacity_usable_for_network']='false; seats/configuration UNKNOWN'
write('route_product_cards.csv',C)
# Explicit foreign-key mapping preserves candidate attribution separately from source collectors.
A=read('adapter_mapping.csv');check('adapter cards reference existing scoped evidence',all(a['card_id'] in {c['card_id'] for c in C} for a in A))
UR=read('ufa_schedule_rules.csv')
check('UFA evidence points to correct combined CSV row',all(UR[int(e['source_row'])-2]['source_id']==e['source_id'] and UR[int(e['source_row'])-2]['flight']==e['flight'] for e in E if e['source_path']=='ufa_schedule_rules.csv'))

# Compare same carrier/frequency evidence, but never infer no competition from missing rows.
summary=[]
for n,role in [('D_SVX8','DIRECT_PROGRAM'),('H_UFA_8','HUB_RAY'),('H_UFA_4','HUB_RAY'),('H_UFA_8','ENDPOINT_OD_VIA_UFA'),('H_UFA_4','ENDPOINT_OD_VIA_UFA')]:
 rr=[v for v in V if n in v['candidate_ids'].split(';') and role in v['market_roles'].split(';')]
 summary.append(dict(candidate_id=n,market_role=role,directed_markets=len(rr),positive_dated_markets=sum(int(v['positive_source_cards'])>0 for v in rr),no_matched_positive_row=sum(int(v['positive_source_cards'])==0 for v in rr),meaning='finite source coverage; not market absence or forecast quality'))
write('coverage_summary.csv',summary)
# UFA displayed durations vs offset-adjusted clocks. The source gives local time; retain failures.
off={'UFA':5,'MRV':3,'GOJ':3,'OMS':6,'NJC':5,'KUF':4};clockfail=[]
for r in U:
 def clk(s):a,b=s.split(':');return int(a)*60+int(b)
 mins=(clk(r['arrival_local'])-off[r['destination']]*60-clk(r['departure_local'])+off[r['origin']]*60)%1440
 if mins!=clk(r['displayed_duration']):clockfail.append(dict(source_id=r['source_id'],source_card=r['source_card'],origin=r['origin'],destination=r['destination'],flight=r['flight'],period_start=r['period_start'],period_end=r['period_end'],displayed_minutes=clk(r['displayed_duration']),clock_derived_minutes=mins,status='SOURCE_CONFLICT; not an accepted block time; preserve both'))
write('ufa_clock_conflicts.csv',clockfail,['source_id','source_card','origin','destination','flight','period_start','period_end','displayed_minutes','clock_derived_minutes','status'])
check('no unresolved UFA clock conflict enters target-week numerical duration',not any(e['source_id']==f['source_id'] and e['flight']==f['flight'] and f['period_start']<=e['date']<=f['period_end'] for f in clockfail for e in E))
result=dict(checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks=checks,raw_hash_verified=sum(r['status']=='ACQUIRED' for r in receipts),pinned_blobs_verified=len(locks),dated_source_rows=len(E),unique_published_service_keys=len(ident),duplicate_source_rows=len(E)-len(ident),clock_conflicting_service_keys=len(conflicts),ufa_source_clock_conflicts=len(clockfail),coverage=summary,acceptance_scope=['RAW_HASH_VERIFIED','EXTRACTION_CHECKED','JOIN_CHECKED'],outside_scope=['independent review','confirmed sales','realized yield','seat configuration','actual flights','observed endpoint demand','2027-28 schedules','network economics/rating replay','MRO contract/capacity acceptance'])
(R/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
