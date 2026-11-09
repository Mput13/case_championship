#!/usr/bin/env python3
"""Offline evidence/structure checks. Explicitly not demand or launch validation."""
from pathlib import Path
from datetime import datetime,timezone
import csv,gzip,hashlib,json,math,subprocess,sys
from jsonschema import Draft202012Validator
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
    artifacts=json.load((ROOT/'artifact_manifest.json').open())['files'];bad_art=[r['path'] for r in artifacts if sha(ROOT/r['path'])!=r['sha256']];check('artifact_manifest',not bad_art,str(bad_art))
    out=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),status='PASS' if not errors else 'FAIL',checks=checks,limits=['No candidate economic forecasts evaluated','No full schedules or fleet availability accepted','Primary observations retain original period and grain','Full front reparse NOT_RUN'])
    (ROOT/'validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':out['status'],'checks':len(checks),'failures':errors}));sys.exit(bool(errors))
if __name__=='__main__':main()
