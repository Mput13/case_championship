#!/usr/bin/env python3
"""Offline public checkpoint validation; held raw is not a published artefact.

Writes versioned content manifest and checks within product_probe_v1 only.
"""
import csv
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
ALLOWED={'content-type','content-length','last-modified','etag','date','cache-control','retry-after'}
DENIED={'cookie','set-cookie','authorization','proxy-authorization'}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(name):return list(csv.DictReader((ROOT/name).open(encoding='utf-8',newline='')))
def public(path):return path.is_file() and not any(x in path.relative_to(ROOT).parts for x in ['raw_hold','__pycache__']) and not path.name.endswith('.pyc')
def safe(obj,path):
    if isinstance(obj,dict):
        for k,v in obj.items():
            # A declared removed marker is not a session value.
            assert not(k.lower() in DENIED and v not in [None,'','REMOVED','REDACTED','[REDACTED]']),f'sensitive header field in {path}'
            if k.lower() in {'headers','response_headers'} and isinstance(v,dict):
                assert {s.lower() for s in v}<=ALLOWED,f'headers whitelist in {path}'
            safe(v,path)
    elif isinstance(obj,list):
        for v in obj:safe(v,path)

def main():
    rules=read('normalized/flight_rules.csv');instances=read('normalized/dated_flights.csv')
    assert len(rules)==len({r['rule_id'] for r in rules})==6
    assert len(instances)==len({r['instance_id'] for r in instances})==12
    idx={r['rule_id']:r for r in rules}
    for r in instances:
        rule=idx[r['rule_id']];a=dt.datetime.fromisoformat(r['departure_local_datetime']);b=dt.datetime.fromisoformat(r['arrival_local_datetime'])
        assert a.isoweekday()==int(rule['weekdays_iso'])
        assert rule['valid_from']<=r['departure_local_date']<=rule['valid_to']
        assert a.astimezone(dt.timezone.utc).isoformat()==r['departure_utc']
        assert b.astimezone(dt.timezone.utc).isoformat()==r['arrival_utc']
        assert int((b-a).total_seconds()/60)==int(r['planned_duration_minutes'])
        assert r['performed_status']==r['inventory_status']=='UNKNOWN'
        assert a.utcoffset()==b.utcoffset()==dt.timedelta(hours=3)
        assert (b.date()-a.date()).days==int(r['arrival_day_offset'])
    outward=[r for r in instances if r['origin_iata']=='KVX' and r['departure_local_date']<='2026-12-13']
    assert [(r['departure_local_date'],r['arrival_local_date']) for r in outward]==[('2026-12-07','2026-12-08'),('2026-12-10','2026-12-11')]
    rec=json.loads((ROOT/'receipts/kvx_timetable_20261109.json').read_text())
    held=ROOT/rec['raw_path']
    if held.exists():
        assert digest(held)==rec['sha256']
        # Direct labelled-text check independent of DOM object traversal.
        raw=held.read_text();blocks=re.split(r'<div\s+class="result__block"[^>]*>',raw)[1:]
        expected=[]
        for b in blocks:
            text=' '.join(re.sub('<[^>]+>',' ',b).split())
            if not re.search(r'Рейс А4601[34]\b',text):continue
            route=re.search(r'Направление (\d{2}:\d{2}) (Минеральные воды|Киров) (\d{2}:\d{2}) (Минеральные воды|Киров) Аэропорт прилета',text)
            assert route
            expected.append((route[1],route[3]))
        assert expected==[(r['departure_local_time'],r['arrival_local_time']) for r in rules]
    stay=read('stay_offer/stay_rules.csv');offers=read('stay_offer/public_offers.csv')
    assert len(stay)==len(offers)==2
    assert all(r['minimum_stay']=='UNKNOWN' for r in stay)
    assert all(r['date_inventory']==r['all_in_itinerary_price']=='UNKNOWN' for r in offers)
    public_files=[p for p in sorted(ROOT.rglob('*')) if public(p) and p.relative_to(ROOT).as_posix() not in {'dataset_manifest.json','verification.json'}]
    for p in public_files:
        if p.suffix=='.json':safe(json.loads(p.read_text()),str(p.relative_to(ROOT)))
        if p.suffix in {'.json','.csv','.md'}:
            text=p.read_text()
            assert '/Users/' not in text,f'local absolute path in public artefact {p.relative_to(ROOT)}'
            assert not re.search(r'\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}',text),f'token pattern in {p.relative_to(ROOT)}'
    held_files=[p for p in ROOT.rglob('*') if p.is_file() and 'raw_hold' in p.relative_to(ROOT).parts]
    report={'checked_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'PASS_OFFLINE_EXTRACTION_AND_CALENDAR_ONLY',
        'flight_rules':len(rules),'planned_flights':len(instances),'outbound_instances_in_window':len(outward),
        'stay_rules':len(stay),'public_stay_tariffs':len(offers),'headers_and_public_paths':'PASS',
        'held_raw_files':len(held_files),'held_raw_bytes':sum(p.stat().st_size for p in held_files),
        'source_conflict':'MonThu current airport vspreviousMonFri; not merged',
        'not_accepted':['performed flights','future inventory','confirmed dated hotel booking','concrete air fare quote','realised revenue','observed OD','predictive edge']}
    (ROOT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    files=[{'path':str(p.relative_to(ROOT)),'sha256':digest(p),'size_bytes':p.stat().st_size} for p in public_files]
    sources=[]
    for p in sorted((ROOT/'receipts').glob('*.json')):
        r=json.loads(p.read_text());sources.append({**r,'receipt_path':str(p.relative_to(ROOT))})
    modules=[]
    for name in ['ground_transfer','stay_offer']:
        m=ROOT/name/'dataset_manifest.json';modules.append({'path':str(m.relative_to(ROOT)),'sha256':digest(m),'scope':'module raw/source details and explicit UNKNOWN; no market acceptance'})
    (ROOT/'dataset_manifest.json').write_text(json.dumps({'schema_version':'c14-product-probe-v1','path_base':'directory containing this manifest',
        'created_at_utc':report['checked_at_utc'],'reference_scope_file':'input_reference_scope.json','scope_file':'table_contract.json',
        'public_files':files,'verification_sha256':digest(ROOT/'verification.json'),'root_sources':sources,'module_manifests':modules,
        'raw_publication_policy':'New held raw excluded from Git; factual extracts, SHA, source URLs and acquisition commands published',
        'acceptance':report['status'],'market_acceptance':'HOLD_UNKNOWN'},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
