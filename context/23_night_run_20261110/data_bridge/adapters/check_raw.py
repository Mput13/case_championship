#!/usr/bin/env python3
"""Verify a bounded set of held raw in place; never copy the raw warehouse.

Checks raw hashes, two weather-station parses, 42 regional tourism source cells,
and the clean municipality join already admitted by the frozen core package.
The municipal check does not assign municipalities to airport catchments.
"""
import csv
import gzip
import hashlib
import io
import json
import subprocess
import zipfile
from collections import defaultdict
from pathlib import Path
from build import OUT, ROOT, PINS, CP, AP


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def blob(role,path):
    return subprocess.check_output(['git','show',PINS[role]+':'+path],cwd=ROOT)


def rows(role,path):
    return list(csv.DictReader(io.StringIO(blob(role,path).decode('utf-8-sig'))))


def zrows(path):
    with zipfile.ZipFile(path) as z:
        member=next(n for n in z.namelist() if n.endswith('.csv'))
        with z.open(member) as f:
            yield from enumerate(csv.DictReader(io.TextIOWrapper(f,encoding='utf-8-sig'),delimiter=';'),2)


def write(name,rr,columns=None):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=columns or list(dict.fromkeys(k for r in rr for k in r)),lineterminator='\n')
        w.writeheader();w.writerows(rr)


def main():
    # Read only the provided parent worktree registry. No thread or agent calls.
    parent=Path('/Users/a/agent-audit-2026-09/case_championship/context/16_agent_research/threads.json')
    threadraw=parent.read_bytes();threads=json.loads(threadraw)
    roots={r['role']:Path(r['worktree'])/'context/16_agent_research'/r['role'] for r in threads}
    registries={r:rows(r,CP+'source_registry.csv' if r=='core' else AP+'source_registry.csv') for r in ['core','alternative']}
    selected={
        'core':['ourairports_airports','branches__operating_evidence__omsk_winter_2026',
                'branches__social_economy__tochno_regions_tourism'],
        'alternative':['noaa_lite_218230-99999-2024','noaa_lite_287220-99999-2024','sibur_geography_20261109','emiss_62073']}
    receipts=[];source_rows=[];paths={}
    for role,ids in selected.items():
        for dataset in ids:
            matches=[r for r in registries[role] if r['dataset_id']==dataset]
            if len(matches)!=1:raise ValueError('Registry ambiguity '+dataset)
            r=matches[0];path=roots[role]/r['raw_path'];expected=r.get('stored_sha256') or r['sha256']
            actual=sha(path) if path.is_file() else None
            receipt=dict(role=role,source_commit=PINS[role],dataset_id=dataset,held_raw_path=str(path),
                         source_url=r['source_url'],raw_bytes=path.stat().st_size if path.is_file() else None,
                         expected_stored_sha256=expected,actual_stored_sha256=actual,
                         raw_status='RAW_HASH_VERIFIED' if actual==expected else 'MISSING_OR_MISMATCH',
                         extraction_status='NOT_REPARSED_IN_THIS_CHECK',source_grain=r['grain'],source_units=r['units'],
                         source_snapshot_time=r.get('retrieved_at_utc',''),source_period=r.get('temporal_coverage',''),
                         license=r.get('license',''),publisher=r.get('organization') or r.get('organisation',''))
            receipts.append(receipt);paths[dataset]=path
            source_rows.append(dict(role=role,source_commit=PINS[role],**r))
    # Same-registry weather expected values are independently recalculated from held bytes.
    weather=rows('alternative',AP+'normalized/weather_monthly_2024.csv');weatherchecks=[]
    for station in ['218230-99999','287220-99999']:
        dataset='noaa_lite_'+station+'-2024';path=paths[dataset]
        sample=defaultdict(list)
        with gzip.open(path,'rt') as f:
            for line in f:
                v=list(map(int,line.split()));sample[f'{v[0]:04d}-{v[1]:02d}'].append(v)
        for w in [r for r in weather if r['station_id']==station]:
            rr=sample[w['month']];temps=[r[4]/10 for r in rr if r[4]!=-9999];winds=[r[8]/10 for r in rr if r[8]!=-9999]
            expected=dict(observed_hours=len({tuple(r[:4]) for r in rr}),observed_days=len({r[2] for r in rr}),
                          temperature_observations=len(temps),wind_observations=len(winds),
                          temperature_below_minus20_count=sum(x < -20 for x in temps),wind_ge12_ms_count=sum(x>=12 for x in winds),
                          temperature_mean_c=round(sum(temps)/len(temps),3) if temps else None)
            for field,value in expected.items():
                source=float(w[field]) if w[field] else None
                ok=(source is None and value is None) or (source is not None and value is not None and abs(source-value)<0.00051)
                weatherchecks.append(dict(station_id=station,month=w['month'],field=field,raw_recomputed=value,
                                          pinned_parsed_value=w[field],status='PASS' if ok else 'FAIL'))
        next(r for r in receipts if r['dataset_id']==dataset)['extraction_status']='12_MONTHS_7_FIELDS_REPARSED; see weather cells for exact scope'
    # Exact native unit / period / region / indicator lookup, not a region-name join.
    context=rows('core',CP+'integration_v1/social/gateway_region_context_2024.csv')
    cross={r['airport_iata']:r for r in rows('core',CP+'integration_v1/social/gateway_region_crosswalk.csv')}
    wanted={int(r['source_row']) for r in context};source={}
    for no,r in zrows(paths['branches__social_economy__tochno_regions_tourism']):
        if no in wanted:source[no]=r
    tourismchecks=[]
    for r in context:
        no=int(r['source_row']);s=source.get(no)
        # Source CSV row locators count the header as row1, as in the frozen core recipe.
        ok=s is not None and s['indicator_code']==r['indicator_code'] and s['year']==r['year'] and s['object_oktmo']==cross[r['airport_iata']]['regional_oktmo']
        ok=ok and float(s['indicator_value'])==float(r['value'])
        unit=s['indicator_unit'] if s else None
        ok=ok and (unit==r['unit_native'] or (unit=='ND' and r['unit_native']=='' and r['unit_missing_reason']))
        tourismchecks.append(dict(airport_iata=r['airport_iata'],source_row=no,indicator=r['indicator_code'],year=r['year'],
                                  raw_value=s['indicator_value'] if s else None,parsed_value=r['value'],raw_unit=unit,
                                  admitted_unit=r['unit_native'],status='PASS' if ok else 'FAIL'))
    next(r for r in receipts if r['dataset_id']=='branches__social_economy__tochno_regions_tourism')['extraction_status']='42_REGIONAL_CELLS_REPARSED;14UNKNOWN_UNITS_REMAIN_HELD'
    # Recheck the accepted municipal key join and numeric cells without copying it into city data.
    municipal=rows('core',CP+'branches/social_economy/normalized/example_join_municipal_2024.csv')
    clean=[r for r in municipal if r.get('municipal_type_agrees')=='True']
    raw_manifest=json.loads(blob('core',CP+'integration_v1/social/input_manifest.json'))
    muni_paths={}
    for dataset in ['tochno_bdmo_municipal_wages','tochno_bdmo_municipal_population']:
        record=next(r for r in raw_manifest['inputs'] if r['path'].endswith('/'+dataset+'.zip'))
        path=roots['core']/record['path'].split('/core/',1)[1];actual=sha(path)
        receipts.append(dict(role='core',source_commit=PINS['core'],dataset_id=dataset,held_raw_path=str(path),
                             source_url=record['source_url'],raw_bytes=path.stat().st_size,expected_stored_sha256=record['sha256'],
                             actual_stored_sha256=actual,raw_status='RAW_HASH_VERIFIED' if actual==record['sha256'] else 'MISSING_OR_MISMATCH',
                             extraction_status='ACCEPTED_MUNICIPAL_NUMERIC_CELLS_ONLY',source_grain='municipality upper level ×2024; NOT city/catchment'))
        muni_paths[dataset]=path
    munichecks=[]
    for dataset,field,rowfield in [('tochno_bdmo_municipal_wages','gross_monthly_wage_rub','wage_source_row'),
                                  ('tochno_bdmo_municipal_population','annual_average_population_persons','population_source_row')]:
        wanted={int(r[rowfield]) for r in clean};selectedraw={}
        for no,r in zrows(muni_paths[dataset]):
            if no in wanted:selectedraw[no]=r
        for r in clean:
            no=int(r[rowfield]);s=selectedraw.get(no)
            typefield='wage_source_mun_type' if dataset.endswith('wages') else 'population_source_mun_type'
            ok=s is not None and s['oktmo']==r['oktmo'] and s['year']==r['year'] and s['mun_type']==r[typefield] and float(s['indicator_value'])==float(r[field])
            munichecks.append(dict(dataset_id=dataset,region_id=r['region_id'],oktmo=r['oktmo'],year=r['year'],
                                   raw_row=no,field=field,parsed_value=r[field],status='PASS' if ok else 'FAIL'))
    write('checks/raw_receipts.csv',receipts)
    write('checks/raw_weather_cells.csv',weatherchecks)
    write('checks/raw_tourism_cells.csv',tourismchecks)
    write('checks/raw_municipal_cells.csv',munichecks)
    write('primary_source_registry.csv',source_rows)
    manifest_inputs=[]
    for role,path in [('core',CP+'source_registry.csv'),('alternative',AP+'source_registry.csv'),
                      ('core',CP+'integration_v1/social/input_manifest.json'),
                      ('core',CP+'branches/social_economy/normalized/example_join_municipal_2024.csv')]:
        b=blob(role,path)
        manifest_inputs.append(dict(role=role,source_commit=PINS[role],source_path=path,
                                    sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),ingestion='PINNED_GIT_BLOB'))
    (OUT/'checks/raw_input_manifest.json').write_text(json.dumps(dict(source_inputs=manifest_inputs,held_raw_receipts='raw_receipts.csv',
             parent_threads_path=str(parent),parent_threads_sha256=hashlib.sha256(threadraw).hexdigest(),
             scope='Selected held raw only, read in place. Parent threads paths do not grant input-version upgrades.'),ensure_ascii=False,indent=2)+'\n')
    tests=[dict(check='RETAINED_RAW_HASHES',status='PASS' if all(r['raw_status']=='RAW_HASH_VERIFIED' for r in receipts) else 'FAIL',rows=len(receipts)),
           dict(check='WEATHER_RAW_SELECTED_STATIONS',status='PASS' if all(r['status']=='PASS' for r in weatherchecks) else 'FAIL',cells=len(weatherchecks),scope='two stations only; no dispatch/label inference'),
           dict(check='TOURISM_RAW_42_ROWS',status='PASS' if all(r['status']=='PASS' for r in tourismchecks) else 'FAIL',rows=len(tourismchecks)),
           dict(check='MUNICIPAL_ACCEPTED_NUMERIC_CELLS',status='PASS' if all(r['status']=='PASS' for r in munichecks) else 'FAIL',cells=len(munichecks),scope='Frozen clean join subset; no airport/catchment mapping')]
    result=dict(checks=tests,failed=sum(r['status']=='FAIL' for r in tests),
                parent_threads_sha256=hashlib.sha256(threadraw).hexdigest(),raw_copied=False,network_used=False,
                outside_scope=['All other weather stations','All municipal rejects','Current source freshness','Statistical predictive gain','Observed final OD'])
    (OUT/'checks/raw_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result['failed']:raise SystemExit(1)


if __name__=='__main__':main()
