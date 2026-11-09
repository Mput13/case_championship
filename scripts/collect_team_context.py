#!/usr/bin/env python3
"""Freeze an auditable city table from team data. No route demand inferred.

Offline: python3 scripts/collect_team_context.py
Optional transport subset: --transport-cache /tmp/.../data_intercity...csv
Historical team files and XLSX remain unchanged.
"""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'context/15_team_update/evidence'

def readcsv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def writecsv(p,rows):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--transport-cache',type=Path);a=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    inputs=[ROOT/'data/processed/longlist.csv',ROOT/'data/processed/kover_days.csv',
        ROOT/'data/manual/longlist_manual.csv',ROOT/'context/11_practical_screening/inputs.json',
        ROOT/'context/11_practical_screening/sources.json',ROOT/'context/07_verification/terra_cities_review/corrected_cities.csv',
        OUT/'parent_verified_facts.json']
    long=readcsv(inputs[0]);closures={r['iata']:r for r in readcsv(inputs[1])}
    old={r['iata']:r for r in json.loads(inputs[3].read_text())['cities']}
    oldsrc={r['id']:r for r in json.loads(inputs[4].read_text())}
    verified={r['iata']:r for r in readcsv(inputs[5])}
    knownbase={'TJM':('Utair','PRIMARY_INDEXED_SELF_REPORT_2026-06-11'),
        'KZN':('Nordwind','REUSED_BASE_EVIDENCE'), 'KJA':('Aeroflot group','REUSED_PRIMARY'),
        'IKT':('S7','REUSED_PRIMARY'), 'VVO':('Aurora; S7','REUSED_PRIMARY'),
        'MRV':('Azimuth','REUSED_PRIMARY_UNDATED'), 'AER':('Azimuth','REUSED_PRIMARY_UNDATED')}
    rows=[]
    for r in long:
        i=r['iata'];k=closures.get(i,{});o=old.get(i,{})
        base,bs=knownbase.get(i,('UNKNOWN','UNKNOWN_NOT_ABSENCE'))
        urls=[r['pax_source_url'],'https://tochno.st/datasets/intercity_connectivity','https://t.me/s/favt_info']
        for sid in o.get('sources',[]):
            if sid in oldsrc:urls.append(oldsrc[sid]['url'])
        if i=='TJM':urls.append('https://www.utair.ru/about/news/yuteyr-i-tyumenskaya-oblast-podpisali-soglashenie-o-razvitii-turizma-na-forume-puteshestvuy-/')
        if verified.get(i,{}).get('base_source_url'):urls.append(verified[i]['base_source_url'])
        zone=r.get('transfer_zone','');knownzone=zone in ['0','0.0','1','1.0']
        # Mixed regimes (e.g. IKT international only) remain qualified evidence, not binary operability.
        zonevalue=zone if knownzone else ''
        admission='REUSED_RRJ95_ADMISSION_DOCUMENT' if i in ['GOJ','KUF','GSV'] else ('RECHECKED_RRJ95_ADMISSION_AND_OPERATION' if i=='UFA' else 'UNKNOWN_REQUIRES_TYPE_DOCUMENT_OR_CURRENT_OPERATION')
        mro='REUSED_RRJ95_DAILY_CHECK_PUBLISHED_CAPACITY_UNKNOWN' if i=='GOJ' else 'UNKNOWN_SCOPE_AND_FREE_CAPACITY'
        hours='H24_REUSED_PRIMARY' if i in ['GOJ','KUF','GSV','UFA'] else 'UNKNOWN'
        reported=int(float(r['pax_2025'])) if r['pax_2025'] else None
        qualifier=r['pax_2025_qualifier'];without=None
        if i=='CEK':reported=2166689;without=2160421;qualifier='includes6268transit; domestic+international2160421'
        count=k.get('last365_days','')
        rows.append(dict(city=r['city'],iata=i,population_proxy=int(float(r['catchment_pop'])) if r['catchment_pop'] else None,
            population_year=2021,population_definition='subset of cities over100k assigned within75km; no passenger demand',
            population_status='TEAM_COMPUTED_FROM_TOCHNO; coverage excludes small settlements',
            airport_pax_2025=reported,pax_qualifier=qualifier,pax_excluding_transit_if_known=without,
            listed_direct_count=r.get('direct_now',''),listed_direct_period='2026 dataset; June-Dec per team description, partly future',
            listed_direct_status='listed supply proxy within team SSJ-distance screen; not all airport destinations or completed flights',
            gap_population_proxy=r.get('gap_pop',''),gap_status='accessibility proxy; unknown rail time may count as gap; NOT_OD',
            base_carrier=base,base_status=bs,
            rw_support_airport='RW_PUBLISHED_SUPPORT_NODE' if i in ['KUF','KZN','AER','MCX'] else 'NOT_LISTED_IN_REUSED_SUPPORT_RELEASE_NOT_PROOF_OF_NO_BASE',
            rrj_admission=admission,line_MRO=mro,transfer_zone_indicator=zonevalue,
            transfer_status='REUSED_QUALIFIED_DESCRIPTION_NOT_RW_CONTRACT' if knownzone else 'UNKNOWN',
            transfer_source=r.get('transfer_source',''),published_hours=hours,
            closure_post_days_last365=count,closure_coverage='2024-11-06..2026-11-09 per team filtered corpus',
            closure_status='NO_MATCHING_INTRO_POSTS_IN_CORPUS_NOT_PROOF_OF_ZERO_EVENTS' if count in ['0','0.0'] else 'COUNT_OF_POST_DAYS_LOWER_BOUND_NOT_CANCELLATION_PROBABILITY',
            closure_source=k.get('source',''),income_value=None,tourism_monthly=None,observed_route_OD=None,
            economic_tourism_OD_status='UNKNOWN_NOT_COLLECTED',contract_free_capacity='UNKNOWN_ALL_CITIES',
            source_urls=';'.join(dict.fromkeys(urls)),accessed='2026-11-09',
            source_status='REUSED_TEAM_DATA_PLUS_PARENT_CHECKS; new technical checks separate'))
    assert len(rows)==20 and len({r['iata'] for r in rows})==20
    writecsv(OUT/'cities_matrix.csv',rows)
    meta={'as_of':'2026-11-09','rows':20,'status':'PASS_JOIN_AND_UNIT_CHECK_NOT_FULL_SOURCE_RECHECK',
        'inputs_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}}
    old_manifest=OUT/'cities_matrix_manifest.json'
    previous=json.loads(old_manifest.read_text()) if old_manifest.exists() else {}
    if not a.transport_cache and previous.get('transport'):
        meta['transport']=previous['transport']
        for name,h in meta['transport'].get('frozen_outputs_sha256',{}).items():
            assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==h, 'Changed frozen transport input: '+name
    if a.transport_cache:
        with a.transport_cache.open(encoding='utf-8-sig',newline='') as f:
            t=list(csv.DictReader(f,delimiter=';'))
        alias={'Москва':'MOW_CITY_NOT_ZIA','Сочи':'AER','Уфа':'UFA','Самара':'KUF','Нижний Новгород':'GOJ',
            'Мурманск':'MMK','Архангельск':'ARH','Омск':'OMS','Саратов':'GSV','Минеральные Воды':'MRV',
            'Екатеринбург':'SVX','Нижневартовск':'NJC','Волгоград':'VOG','Челябинск':'CEK','Тюмень':'TJM','Пермь':'PEE'}
        subset=[]
        for r in t:
            if r.get('city_from') not in alias or r.get('city_to') not in alias:continue
            cm=r.get('comment','');codes=re.findall(r'\b[A-Z0-9]{3}\b',cm)
            subset.append(dict(city_from=r['city_from'],city_to=r['city_to'],origin_proxy=alias[r['city_from']],destination_proxy=alias[r['city_to']],
                transport_type=r.get('transport_type'),model_distance_km=r.get('distance_km'),model_time_hr=r.get('distance_hr'),
                missing_reason=r.get('missing_reason'),source_comment=cm,comment_airport_codes=';'.join(codes),
                status='MODELLED_TIME_NOT_TIMETABLE; air listed supply not performed service or demand',
                source_url='https://tochno.st/datasets/intercity_connectivity',version='2026-06-29',accessed='2026-11-09'))
        assert subset
        writecsv(OUT/'transport_pair_proxies.csv',subset)
        wanted={r['iata'] for r in rows}|{'SVX','ZIA','ARH','MMK','NJC','SVO','DME','VKO'}
        air={}
        for rr in t:
            if rr.get('transport_type')!='air' or not rr.get('distance_km'):continue
            mm=re.match(r'\s*([A-Z0-9]{3})\s*—\s*([A-Z0-9]{3})',rr.get('comment',''))
            if not mm:continue
            x,y=mm.groups()
            if x not in wanted or y not in wanted:continue
            key=(x,y,rr.get('source',''))
            if key not in air:
                air[key]=dict(origin=x,destination=y,data_source=rr.get('source',''),source_comment=rr.get('comment',''),city_edge_count=0,status='AGGREGATE_ROUTE_LIST_NOT_CURRENT_TIMETABLE_OR_DEMAND',source_url='https://tochno.st/datasets/intercity_connectivity',version='2026-06-29',accessed='2026-11-09')
            air[key]['city_edge_count']+=1
        writecsv(OUT/'air_presence_aggregate.csv',[air[k] for k in sorted(air)])
        meta['transport']={'source_sha256':hashlib.sha256(a.transport_cache.read_bytes()).hexdigest(),'source_rows':len(t),'subset_rows':len(subset),'unit':'modeled city-pair hours and km, not actual schedules or airport access','listed_airport_edges':len(air),'frozen_outputs_sha256':{n:hashlib.sha256((OUT/n).read_bytes()).hexdigest() for n in ['transport_pair_proxies.csv','air_presence_aggregate.csv']}}
    (OUT/'cities_matrix_manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(meta,ensure_ascii=False))

if __name__=='__main__':main()
