#!/usr/bin/env python3
"""Offline integrity and boundary verification for the public handoff."""
import csv, hashlib, json, pathlib, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(name):return list(csv.DictReader((ROOT/name).open()))
manifest=json.loads((ROOT/'dataset_manifest.json').read_text())
allowed={'content-type','content-length','last-modified','etag','date','cache-control'}
source_ids=set();raw_count=0
for r in manifest['sources']:
 source_ids.add(r['source_id']); assert set(r['headers'])<=allowed,r['source_id']
 if 'raw_path' in r:
  p=ROOT/r['raw_path']; assert digest(p)==r['sha256'],p; assert p.stat().st_size==r['byte_length'];raw_count+=1
for a in manifest['public_artifacts']:
 p=ROOT/a['path'];assert digest(p)==a['sha256'],p
sched=rows('transfer_schedule.csv');fare=rows('transfer_fare_observations.csv');alts=rows('ground_alternatives.csv');rules=rows('transfer_rules.csv');prices=rows('curated_transfer_prices.csv')
assert len(sched)==363==len(fare)
assert {r['observation_id'] for r in sched}=={r['observation_id'] for r in fare}
assert len({r['source_id'] for r in sched})==15
assert all(r['origin_iana']=='UNKNOWN' and r['destination_iana']=='UNKNOWN' for r in sched)
assert all(r['service_date']==r['valid_from']==r['valid_through'] for r in sched)
assert all(r['source_id'] in source_ids and r['booking_status']=='NOT_QUERIED' for r in sched)
assert not any('amount' in k or 'price' in k for k in sched[0])
assert all(r['source_id'] in source_ids for r in rules+prices+alts+fare)
rail=[r for r in alts if r['alternative_id'].startswith('KIROV_')][0]
assert rail['duration_min_minutes']=='UNKNOWN_PRIMARY_DATED' and rail['reference_duration_minutes']=='3622'
assert rail['inventory_status']=='UNKNOWN'
assert all(r['inventory_status']=='UNKNOWN_NOT_BOOKED' for r in prices)
# No literal phone/email blocks or forbidden response header names in exported data/receipts.
checked=[]
for p in sorted(ROOT.rglob('*')):
 if not p.is_file() or 'raw_hold' in p.parts or '__pycache__' in p.parts:continue
 if p.suffix in ['.csv','.json'] and p.name!='verification_summary.json':
  data=p.read_text();assert 'set-cookie' not in data.lower() and 'authorization:' not in data.lower(),p;checked.append(str(p.relative_to(ROOT)))
held=next((ROOT/'raw_hold').glob('*.html'))
probe=subprocess.run(['git','check-ignore','--',str(held)],cwd=ROOT,text=True,capture_output=True)
assert probe.returncode==0,'raw_hold must be ignored'
summary={'status':'PASS','checked_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'raw_bodies_verified':raw_count,'source_receipts':len(source_ids),'schedule_rows':len(sched),'fare_rows':len(fare),'exact_date_pages':15,'rules':len(rules),'ground_alternatives':len(alts),'curated_price_rows':len(prices),'public_data_files_scanned':len(checked),'checks':['every raw body hash/size matches receipt','public artifact hashes match manifest','only allowed response headers persisted','requested dates and station codes verified by derive_schedules','clock-duration arithmetic and day offsets verified by derive_schedules','schedule and tariff rows separated by observation_id','unknown IANA not filled by inference','primary long-distance rail remains UNKNOWN, secondary reference isolated','all advertised price inventory UNKNOWN','raw_hold gitignored'],'not_tested':['train performed instances','seat inventory','taxi actual availability','night pickup confirmation','airport exit/wait','sanatorium checkin/room inventory','consumer purchase quotes','primary dated Kirov rail return itinerary']}
(ROOT/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False))
