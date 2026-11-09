#!/usr/bin/env python3
"""Offline evidence/structure checks. Explicitly not demand or launch validation."""
from pathlib import Path
from datetime import datetime,timezone
import csv,gzip,hashlib,json,math,subprocess,sys
from jsonschema import Draft202012Validator
from publication_headers import PUBLIC_HEADERS, forbidden_key
ROOT=Path(__file__).resolve().parents[1]
def read(name):return list(csv.DictReader((ROOT/name).open()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    errors=[];checks=[]
    def check(name,ok,detail=''):
        checks.append(dict(check=name,status='PASS' if ok else 'FAIL',detail=detail))
        if not ok:errors.append(name)
    cat=json.load((ROOT/'inputs/candidate_catalog.json').open())['candidates'];schema=json.load((ROOT/'candidate_schema.json').open())
    Draft202012Validator.check_schema(schema);validator=Draft202012Validator(schema)
    invalid=[(c['candidate_id'],e.message) for c in cat for e in validator.iter_errors(c)]
    check('schema',not invalid,str(invalid))
    wrong=dict(cat[0]);wrong['demand_value']=100
    check('schema_rejects_unknown_numeric_demand',bool(list(validator.iter_errors(wrong))))
    old={r['id'] for r in read('existing_hypotheses.csv')};bad=[(c['candidate_id'],a) for c in cat for a in c['ancestor_ids'].split(';') if a not in old]
    check('ancestor_join_no_unmatched',not bad,str(bad))
    data_ids={r['data_id'] for r in read('data_requests.csv')}
    check('D01_D30_exact_coverage',data_ids=={f'D{i:02}' for i in range(1,31)})
    check('nine_distinct_deepening_tests',len(read('experiments_queue.csv'))==9 and sum(c['selected_for_deepening'] for c in cat)==9)
    check('unknowns_not_imputed',all(c['demand_value'] is None and c['net_fare_rub'] is None and c['available_aircraft'] is None and c['evaluation_status']=='NOT_EVALUATED' for c in cat))
    check('no_political_dates',all(c['political_change_date'] is None for c in cat))
    evidence={r['observation_id'] for r in read('contributions/source_access/observations.csv')}|{r['dataset_id'] for r in json.load((ROOT/'dataset_manifest.json').open())['datasets']}
    check('evidence_ids_resolve',all(a in evidence for c in cat for a in c['primary_evidence_ids'].split(';') if a))
    manifest=json.load((ROOT/'dataset_manifest.json').open());bad_hash=[r['dataset_id'] for r in manifest['datasets'] if r.get('raw_path') and sha(ROOT/r['raw_path'])!=r['sha256']]
    check('raw_hashes',not bad_hash,str(bad_hash))
    g=json.load((ROOT/'inputs/geometry_manifest.json').open());raw=gzip.decompress((ROOT/g['raw_path']).read_bytes());check('raw_decompression_hash',hashlib.sha256(raw).hexdigest()==g['uncompressed_sha256'])
    import io
    subset=[r for r in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))) if r['iso_country']=='RU']
    check('RU_subset_exact_reproduction',subset==read('normalized/airports_ru.csv'))
    check('airports_unique_and_wide',len(read('normalized/city_scope.csv'))>=10 and len({r['airport_id'] for r in read('normalized/city_scope.csv')})==len(read('normalized/city_scope.csv')))
    # Independent spherical law of cosines versus the haversine outputs.
    coords={r['airport_iata']:(math.radians(float(r['latitude_deg'])),math.radians(float(r['longitude_deg']))) for r in read('normalized/city_scope.csv')};deltas=[]
    for r in read('normalized/geometry_legs.csv'):
        (a,b),(c,d)=coords[r['origin']],coords[r['destination']]
        km=6371.0088*math.acos(max(-1,min(1,math.sin(a)*math.sin(c)+math.cos(a)*math.cos(c)*math.cos(d-b))))
        deltas.append(abs(km-float(r['distance_km'])))
    check('geometry_independent_formula',max(deltas)<0.00051,f'max error km={max(deltas)}')
    import re
    schedule=read('normalized/khv_arrival_rules.csv');check('schedule_shape_and_dates',all(re.fullmatch(r'\d{2}\.\d{2}\.\d{4} - \d{2}\.\d{2}\.\d{4}',r['validity_raw']) and r['operating_carrier']=='UNKNOWN' for r in schedule),f'{len(schedule)} literal arrival rules; no frequency inference')
    thresholds=read('normalized/reproduced_thresholds.csv');check('scenario_threshold_reproduction',len(thresholds)==4 and {int(r['required_pax_before_fixed']) for r in thresholds}=={85,180})
    check('external_raw_ignored',subprocess.run(['git','check-ignore','-q',str(ROOT/g['raw_path'])]).returncode==0)
    runs=[json.loads(l) for l in (ROOT/'evaluation_runs.jsonl').read_text().splitlines()]
    check('all_attempt_inputs_preserved',all(sha(ROOT/'inputs/run_snapshots'/(h+'.blob'))==h for run in runs for h in run['input_hashes'].values()))
    public_files=['dataset_manifest.json','contributions/source_access/dataset_manifest_public.json','contributions/source_access/public_receipts.json','contributions/existing_map/review_evidence/front_audit_20261109/primary_manifest_public.json']
    def safe_metadata(value):
        if isinstance(value,list):return all(safe_metadata(v) for v in value)
        if not isinstance(value,dict):return True
        return all(not forbidden_key(k) and (k.casefold()!='headers' or isinstance(v,dict) and all(h.casefold() in PUBLIC_HEADERS for h in v)) and safe_metadata(v) for k,v in value.items())
    check('published_metadata_keys_and_header_whitelist',all(safe_metadata(json.loads((ROOT/p).read_text())) for p in public_files))
    transforms=json.loads((ROOT/'publication_transforms.json').read_text())['transformations']
    check('original_and_stored_metadata_hashes',all(sha(ROOT/item['path'])==item['sha256'] for t in transforms for item in t['originals']+[t['stored']]))
    local_raw=json.loads((ROOT/'publication_review.json').read_text())['local_only']
    check('all_local_originals_unchanged',all(sha(ROOT/r['path'])==r['sha256'] for r in local_raw))
    # Exercise the collector with an in-memory HTTP response; never make a request.
    import email.message,importlib.util,tempfile
    from unittest.mock import patch
    spec=importlib.util.spec_from_file_location('publication_collector',ROOT/'contributions/source_access/collectors/acquire.py')
    collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)
    headers=email.message.Message()
    for key,value in [('Content-Type','text/html; charset=utf-8'),('Date','Mon, 09 Nov 2026 00:00:00 GMT'),('sEt-CoOkIe','fixture-only'),('Authorization','fixture-only'),('X-Unknown-Header','fixture-only')]:headers[key]=value
    body=b'<p>Unmodified body fixture</p>'
    class Response:
        status=200;url='https://example.invalid/offline-fixture'
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def read(self,*args):return body
    response=Response();response.headers=headers
    with tempfile.TemporaryDirectory(dir=ROOT/'raw/external',prefix='publication-check-') as temp:
        collector.ROOT=Path(temp);(collector.ROOT/'raw').mkdir()
        with patch.object(collector.urllib.request,'urlopen',return_value=response):
            row=collector.acquire({'dataset_id':'FIXTURE','source_url':response.url})
        receipt=json.loads((collector.ROOT/'raw/FIXTURE_receipt.json').read_text())
        ok=row['acquisition_status']=='ACQUIRED_RAW' and row['headers']=={'Content-Type':headers['Content-Type'],'Date':headers['Date']} and safe_metadata(receipt) and (collector.ROOT/'raw/FIXTURE.html').read_bytes()==body and row['sha256']==hashlib.sha256(body).hexdigest()
    check('collector_offline_headers_and_original_body',ok)
    artifacts=json.load((ROOT/'artifact_manifest.json').open())['files'];bad_art=[r['path'] for r in artifacts if sha(ROOT/r['path'])!=r['sha256']];check('artifact_manifest',not bad_art,str(bad_art))
    out=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),status='PASS' if not errors else 'FAIL',checks=checks,limits=['No candidate economic forecasts evaluated','No full schedules or fleet availability accepted','Primary observations retain original period and grain','Full front reparse NOT_RUN'])
    (ROOT/'validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':out['status'],'checks':len(checks),'failures':errors}));sys.exit(bool(errors))
if __name__=='__main__':main()
