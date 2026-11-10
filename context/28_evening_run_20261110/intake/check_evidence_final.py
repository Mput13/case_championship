#!/usr/bin/env python3
"""Bounded root intake of final sources; not independent source/market review."""
import csv
import hashlib
import io
import json
import math
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

SHA='38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b'
ROOT='context/28_evening_run_20261110/evidence/'
def blob(s,p): return subprocess.check_output(['git','show',s+':'+p])
def data(p): return blob(SHA,ROOT+p)
def rows(p): return list(csv.DictReader(io.StringIO(data(p).decode())))

inputs=json.loads(data('input_manifest.json'))
for r in inputs:
    b=data(r['snapshot'])
    assert b==blob(r['commit'],r['path'])
    assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
outputs=json.loads(data('output_manifest.json'))['files']
for r in outputs:
    b=data(r['path'])
    assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
registry=rows('source_registry.csv');raws=texts=0
for r in registry:
    receipt=json.loads(data(r['receipt_path']))
    assert r['source_id']==receipt['source_id'] and r['url']==receipt['url']
    if r['raw_path']:
        b=data(r['raw_path']);raws+=1
        assert hashlib.sha256(b).hexdigest()==r['sha256']==receipt['sha256'] and len(b)==int(r['bytes'])
    if r['text_path']:
        texts+=1
        assert hashlib.sha256(data(r['text_path'])).hexdigest()==r['text_sha256']==receipt['text_sha256']
pairs=rows('pair_registry.csv');links=rows('pair_hypothesis_join.csv')
assert len(pairs)==45 and len({r['route'] for r in pairs})==45
assert all(x['route'] in {r['route'] for r in pairs} for x in links)
assert {x['hypothesis'] for x in links}=={'C01','C03','C04','C07','C10','C14','C17','C31','C33','C35'}
records=rows('dated_service_records.csv');instances=rows('dated_service_instances.csv')
def key(r): return tuple(r[k] for k in ('origin','destination','date','flight'))
grouped=defaultdict(list)
for r in records: grouped[key(r)].append(r)
assert len(instances)==len(grouped)==215
assert len({key(r) for r in instances})==len(instances)
for r in instances:
    g=grouped[key(r)]
    assert len(g)==int(r['publication_records']) and r['oneway_departures']=='1'
    assert set(r['source_ids'].split(';'))=={x['source_id'] for x in g}
    for k in ('departure_local','arrival_local','aircraft'):
        assert set(r[k].split(' | '))=={x[k] for x in g},(key(r),k,r[k],{x[k] for x in g})
assert len(records)-len(instances)==144
assert sum(r['clock_or_type_conflict']=='True' for r in instances)==12
weekly=rows('weekly_service_context.csv')
assert sum(int(r['oneway_departures']) for r in weekly)==len(instances)
sample=[r for r in instances if r['flight']=='FV-6846' and r['origin']=='OMS' and r['destination']=='KJA']
# Flight IDs retain their original punctuation; match numeric code as a fallback.
if not sample: sample=[r for r in instances if '6846' in r['flight'] and r['origin']=='OMS' and r['destination']=='KJA']
assert len(sample)==2
assert {r['date'] for r in sample}=={'2026-12-07','2026-12-12'}
assert all(r['departure_local']=='01:30' and r['arrival_local']=='04:35' for r in sample)
rules=data('raw/web/favt_regional_rules/text.txt').decode()
assert 'на все места в салоне экономического класса' in rules
assert 'количества выполненных рейсов' in rules
fare=rows('subsidy_special_fare_grid.csv');caps=rows('subsidy_cap_84_103_seats.csv');examples=rows('subsidy_cap_examples.csv')
for r in examples:
    km=float(r['official_km'])
    f=next(x for x in fare if float(x['min_km'])<=km<=(float(x['max_km']) if x['max_km'] else math.inf))
    c=next(x for x in caps if float(x['min_km'])<=km<=(float(x['max_km']) if x['max_km'] else math.inf))
    assert float(r['base_special_fare_rub_including_vat'])==float(f['base_special_fare_rub_including_vat'])
    assert float(r['appendix1_cap_rub_oneway'])==float(c['cap_rub_per_oneway_flight'])
    assert r['joint_fare_condition'] and r['actual_RW_award'].startswith('UNKNOWN')
app=rows('subsidy_applicability.csv')
assert len(app)==45 and all('ALL economy' in r['joint_fare_obligation'] for r in app)
result={'subject_sha':SHA,'status':'COORDINATOR_INTAKE_PASS_INDEPENDENT_REVIEW_PENDING','checks':{'git_inputs':len(inputs),'output_hashes':len(outputs),'receipts':len(registry),'raw_hashes':raws,'text_hashes':texts,'pairs':len(pairs),'links':len(links),'dated_records':len(records),'unique_departures':len(instances),'duplicates_not_summed':144,'conflicts_retained':12,'weekly_rows':len(weekly),'joint_cap_fare_examples':len(examples),'real_sample':'FV6846 OMS-KJA Mon/Sat01:30-04:35 preserved'},'not_run':['independent HTML/XLSX full reparse','full primary legal/applicability review','actual flights/fares/seats','2027-2028 awards or cash','complete market or free fleet'],'limits':['Historical schedule is not free resource','Source versions are distinct, not retrospective author errors','22 coverage gaps do not establish absence of service','Grant cap and all-economy special fare apply jointly; retail/net bridge remains necessary']}
Path(__file__).with_name('evidence_final_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
