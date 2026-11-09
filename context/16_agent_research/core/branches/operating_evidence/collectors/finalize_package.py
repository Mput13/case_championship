#!/usr/bin/env python3
"""Finalize local operating-evidence metadata and integrity checks, without network.

Raw snapshots are never altered. The caller first runs normalize.py and supplement.py.
"""
import collections
import csv
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'normalized'
SAFE_HEADERS={'content-type','content-length','last-modified','etag','date','cache-control'}
ALLOWED_STATUS={'LEAD','ACCESS_FAILED','ACQUIRED_RAW','PARSED','VALIDATED','RESTRICTED_USE'}

def now():return datetime.now(timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def read(name):return list(csv.DictReader((OUT/name).open()))
def write(path,rows,fields=None):
    rows=list(rows);fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(rows)

def main():
    stamp=now();manifest=json.loads((ROOT/'dataset_manifest.json').read_text())
    # These are local dependencies/diagnostics rather than newly acquired websites.
    additions=[
      ('parent_canonical_keys_snapshot','raw/parent_canonical_keys_snapshot.csv','local:context/16_agent_research/core/canonical_keys.csv','airport/city identity crosswalk snapshot','Pinned parent OurAirports/Travelpayouts keys; directory assertion, not official certification. Keep this historical dependency unchanged.'),
      ('native_web_access_diagnostic','raw/native_web_error.txt','https://mai-way.ru/tasks/red-wings/','diagnostic log','Native web open path failed; ordinary urllib downloaded the page. Root cause UNKNOWN; no browser, process, profile or MCP modifications.')]
    known={e['dataset_id'] for e in manifest}
    for id,path,url,grain,limits in additions:
        if id in known:continue
        f=ROOT/path;b=f.read_bytes()
        manifest.append(dict(dataset_id=id,source_url=url,raw_path=path,sha256=sha(b),size_bytes=len(b),retrieved_at_utc=datetime.fromtimestamp(f.stat().st_mtime,timezone.utc).isoformat(),publication_date='UNKNOWN',organization='Core research working snapshot' if id.startswith('parent_') else 'T3 native tool diagnostic',grain=grain,geographic_coverage='Russia; source scope retained' if id.startswith('parent_') else 'N/A',temporal_coverage='Pinned 2026-11-09 dependency' if id.startswith('parent_') else '2026-11-09 tool access observation',record_count=None,acquisition_status='ACQUIRED_RAW',limitations=limits,license='UNKNOWN',decision_use='Reproduce local key resolution' if id.startswith('parent_') else 'Explain HTTP fallback without changing sessions',collector_version='finalize-package-v1',command='python3 context/16_agent_research/core/branches/operating_evidence/collectors/finalize_package.py'))
    table_specs={
      'uvt_schedule_current':('uvt_schedule_rules_unique.csv','published direction x flight x validity x weekdays','origin_city;destination_city;flight;validity','local clock HH-MM; departures/week/direction','All listed endpoint tables; 153 unique directional rules from 150 paired source rows; includes international endpoints','Published validity per row; current HTML retrieved 2026-11-09'),
      'favt_regional_2026':('favt_subsidy_2026_full.csv','programme route x carrier x period/type row','route_number;carrier;endpoints;period;source_row','oneway km; seats; weekly frequency convention unresolved; paired flights/year','306 numbered route groups, 19 carrier labels, 90 airport names','2026 plan as published at retrieval; not paid award or execution'),
      'svx_schedule':('svx_published_schedule_rules.csv','SVX departure rule','flight;destination;validity_raw;weekdays;source_row','clock HH:MM; departures/week in one direction','SVX -> 83 airport codes; 31 carrier labels; 80 RED WINGS rows','Year missing in row validity; raw day/month range retained without winter-year inference'),
      'azimuth_board':('azimuth_flight_instances.csv','carrier board displayed flight instance','flight;origin;destination;displayed departure date','displayed clock; planned/reported actual separately','185 board rows; 81 status Прибыл; neither full network nor reliability sample','Visible labels 8-11 Nov 2026; year context-derived, clock basis UNKNOWN'),
      'omsk_winter_2026':('omsk_domestic_timetable_rows.csv','airport domestic paired/through rule','flight pair;routing;period;weekdays;source line','local clock; weekdays ISO1-7','76 parsed domestic rows plus 1 retained exception, 13 carriers; international section not parsed','PDF w26-20261105; explicit rule dates; OMS week 7-13Dec2026 expanded separately'),
    }
    iraero=read('iraero_published_itineraries.csv')
    for id in sorted({r['source_dataset_id'] for r in iraero}):
        selected=[r for r in iraero if r['source_dataset_id']==id]
        table_specs[id]=('iraero_published_itineraries.csv','origin-filtered published endpoint itinerary','origin;destination;flight;date;source_row','displayed clock basis UNKNOWN; date; type label','Origin '+','.join(sorted({r['origin_code_raw'] for r in selected}))+'; endpoint offer may include stops',min(r['departure_date'] for r in selected)+'/'+max(r['departure_date'] for r in selected))
    for e in manifest:
        e.setdefault('key_fields','dataset_id;snapshot;source_row as applicable')
        e.setdefault('units','N/A: documentation/HTML; see normalized row units')
        e.setdefault('publication_date','UNKNOWN')
        e.setdefault('accessibility','public HTTP GET without auth' if e.get('http_status')==200 else 'git snapshot' if e.get('git_ref') else e['acquisition_status'])
        e['path_base']='.'
        if isinstance(e.get('response_headers'),dict):e['response_headers']={k:v for k,v in e['response_headers'].items() if k.lower() in SAFE_HEADERS}
        id=e['dataset_id']
        if id in table_specs:
            file,grain,key,units,geo,period=table_specs[id]
            e.update(grain=grain,key_fields=key,units=units,geographic_coverage=geo,temporal_coverage=period,parse_status='PARSED',normalized_path='normalized/'+file)
            e['parsed_record_count']=len([r for r in iraero if r['source_dataset_id']==id]) if id.startswith('iraero_') else len(read(file))
            e['record_count_basis']='raw CSV record count when given; HTML/PDF file record_count null, parsed_record_count explicit'
        if id.startswith('colleague_'):
            e['acquisition_status']='RESTRICTED_USE';e['decision_use']='Lineage and reproducible parser-contamination evidence only; facts HOLD'
            e['limitations']='PARSER_CONTAMINATION; front fetch_telegram.py can select reply preview instead of main js-message_text. Original bytes preserved. No event, route or guaranteed lower-bound claim is accepted from these CSVs.'
        if id=='parent_canonical_keys_snapshot':
            e['record_count']=sum(1 for _ in csv.DictReader((ROOT/e['raw_path']).open()))
        if id=='iraero_schedule':e['limitations']='Origin IKT endpoint listing; same flight can reach multiple destinations with intermediate stops. Actual clock basis and displayed duration not validated; do not use as UTC, nonstop capacity or block time.'
        if id in ['ufa_services_20261111','ufa_fuel_20261111']:
            e['effective_from']='2026-11-11';e['decision_use']='Selected public UFA tariff inputs and sensitivity bounds, not a paid RW cost basket'
        if id.startswith('omsk_tariff_') and id!='omsk_tariff_index':e['decision_use']='Omsk airport public tariff components with base/revision dates and VAT basis'
    (ROOT/'dataset_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    fields=['dataset_id','organization','source_url','retrieved_at_utc','publication_date','grain','geographic_coverage','temporal_coverage','key_fields','units','acquisition_status','parse_status','license','accessibility','raw_path','sha256','size_bytes','record_count','parsed_record_count','collector_version','command','decision_use','limitations']
    write(ROOT/'source_registry.csv',manifest,fields)
    coverage=[]
    for e in manifest:
        coverage.append(dict(dataset_id=e['dataset_id'],source_url=e['source_url'],geographic_coverage=e['geographic_coverage'],temporal_coverage=e['temporal_coverage'],grain=e['grain'],raw_record_count=e.get('record_count'),parsed_record_count=e.get('parsed_record_count'),acquisition_status=e['acquisition_status'],normalized_path=e.get('normalized_path',''),limits=e['limitations']))
    write(ROOT/'coverage.csv',coverage)
    rejected=[]
    for e in manifest:
        if e['acquisition_status'] in ['ACCESS_FAILED','RESTRICTED_USE']:
            rejected.append(dict(dataset_id=e['dataset_id'],source_url=e['source_url'],status=e['acquisition_status'],exact_error=e.get('exact_error',''),reason=e['limitations'],usable_surrogate='Independent published schedule/airport PDF only; no inference from absence' if e['acquisition_status']=='RESTRICTED_USE' else 'Use downloaded alternative URL when available; no failed source replaced by zeros'))
    for id,reason in [
       ('iraero_self_endpoint_and_non_latin_codes','1 self-endpoint row and 9 non-Latin destination-code rows retained in source table; exclude from route inventory until manually resolved'),
       ('iraero_multistop_ambiguity','304 flight-origin-date groups have several destination endpoints; conversion to nonstop legs or summed capacity is HOLD'),
       ('uvt_arrival_clock_conflicts','2 calendar keys have conflicting arrival clocks; HOLD arrival value, preserve both source representations'),
       ('svx_validity_year','Row validity omits year; matched Dec2026 frequency HOLD until year or dated independent corroboration obtained'),
       ('azimuth_clock_basis','Clock basis not established in saved board; UTC/block duration derivation HOLD'),
       ('omsk_one_leg_exception','1 PDF domestic line kept as exception; not fabricated into return rotation')]:
        rejected.append(dict(dataset_id=id,source_url='',status='RESTRICTED_USE',exact_error='',reason=reason,usable_surrogate='Retain original strings/rows and resolve only selected candidate before network acceptance'))
    write(ROOT/'rejected_or_unavailable.csv',rejected)
    aliases=[]
    for code,name,file,field,prefix in [('WZ','RED WINGS','svx_published_schedule_rules.csv','carrier_raw','WZ-'),('RT','ЮВТ Аэро','uvt_schedule_rules_unique.csv','carrier','RT-'),('IO','ИрАэро','iraero_published_itineraries.csv','carrier','IO-'),('A4','Азимут','azimuth_flight_instances.csv','carrier','A4')]:
        rr=read(file);hits=[r for r in rr if r.get(field)==name]
        aliases.append(dict(carrier_key='RESEARCH-CARRIER:'+code,published_name=name,published_designator=code,source_name_field=field,source_path='normalized/'+file,matching_rows=len(hits),evidence='Publisher carrier label and matching flight-number prefix '+prefix,alias_status='SOURCE_SUPPORTED_LABEL_AND_PREFIX',identity_limit='Not an official IATA/legal certificate registry; actual operating carrier per individual code-share flight needs confirmation',value_status='DERIVED'))
    write(OUT/'carrier_source_aliases.csv',aliases)
    refs=dict(checked_at_utc=stamp,front='71b493d0051dc3acf2a7619801e5b0eb022bddd3',specified_team_update='83c2698ebebc172fd8f1d0b8a82b8bd07f8da791',reviewed_team_update='bf564c7b66a2559c21e9f519ae5a3f28a489378f',kiruha_sources='5e896e8ea5bb97136c71c49562a345b8f210bf11',parent_pinned_key_sha256=sha((ROOT/'raw/parent_canonical_keys_snapshot.csv').read_bytes()),integration_note='Parent handles final git fetch and checkpoint publication; no child commit/push/merge or new acquisition in finalization')
    (ROOT/'input_refs.json').write_text(json.dumps(refs,indent=2)+'\n')
    artifacts=[]
    for f in sorted(OUT.iterdir()):
        if not f.is_file():continue
        b=f.read_bytes();n=len(read(f.name)) if f.suffix=='.csv' else None
        artifacts.append(dict(path=str(f.relative_to(ROOT)),sha256=sha(b),size_bytes=len(b),record_count=n))
    normalized=dict(generated_at_utc=stamp,path_base='.',artifacts=artifacts,commands=['python3 context/16_agent_research/core/branches/operating_evidence/collectors/normalize.py','python3 context/16_agent_research/core/branches/operating_evidence/collectors/supplement.py','python3 context/16_agent_research/core/branches/operating_evidence/collectors/finalize_package.py'],collector_hashes={f.name:sha(f.read_bytes()) for f in sorted((ROOT/'collectors').glob('*.py'))})
    (ROOT/'normalized_manifest.json').write_text(json.dumps(normalized,ensure_ascii=False,indent=2)+'\n')
    rawchecks=[]
    for e in manifest:
        if not e.get('raw_path'):continue
        f=ROOT/e['raw_path'];b=f.read_bytes();rawchecks.append(dict(dataset_id=e['dataset_id'],path=e['raw_path'],sha256_match=sha(b)==e['sha256'],size_match=len(b)==e['size_bytes']))
    bad=[]
    def scan(v,path):
        if isinstance(v,dict):
            for k,q in v.items():
                if k.lower() in ['cookie','set-cookie','authorization','proxy-authorization']:bad.append(path+'/'+k)
                if k=='response_headers' and isinstance(q,dict):
                    bad.extend(path+'/'+k+'/'+h for h in q if h.lower() not in SAFE_HEADERS)
                scan(q,path+'/'+k)
        elif isinstance(v,list):
            for i,q in enumerate(v):scan(q,path+'/'+str(i))
    scan(manifest,'dataset_manifest')
    unknown_status=[e['dataset_id'] for e in manifest if e['acquisition_status'] not in ALLOWED_STATUS]
    check=dict(checked_at_utc=stamp,path_base='.',raw_checks=rawchecks,raw_files=len(rawchecks),raw_bytes=sum((ROOT/e['raw_path']).stat().st_size for e in manifest if e.get('raw_path')),normalized_files=len(artifacts),normalized_bytes=sum(a['size_bytes'] for a in artifacts),forbidden_header_fields=bad,unknown_acquisition_status=unknown_status,all_raw_integrity_pass=all(c['sha256_match'] and c['size_match'] for c in rawchecks),raw_payloads_modified=False,acceptance_limit='Integrity and parser structural checks only; no observed OD, paid net fares, free fleet, negotiated costs or full network capacity verified')
    (ROOT/'manifest_validation.json').write_text(json.dumps(check,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:check[k] for k in ['raw_files','raw_bytes','normalized_files','normalized_bytes','forbidden_header_fields','all_raw_integrity_pass']},ensure_ascii=False))
    if bad or unknown_status or not check['all_raw_integrity_pass']:raise SystemExit(1)
if __name__=='__main__':main()
