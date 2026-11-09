#!/usr/bin/env python3
"""Expose stale timezone assertions using an independent gazetteer and IANA source.

Nearest-city checks are diagnostic only. They do not draw timezone boundaries.
Conflicting offsets are removed from the usable field; source assertion is retained.
Run after normalize_core.py; safe and deterministic when repeated.
"""
import csv
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile
from zoneinfo import ZoneInfo, TZPATH

ROOT=Path(__file__).resolve().parents[1]
N=ROOT/'normalized'
def hav(a,b,c,d):
    a,b,c,d=map(math.radians,map(float,(a,b,c,d)))
    return 12742*math.asin(min(1,math.sqrt(math.sin((c-a)/2)**2+math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2)))
def read(p):return list(csv.DictReader(p.open()))
def emit(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def offset(tz):
    if not tz:return None
    return int(dt.datetime(2026,12,7,tzinfo=ZoneInfo(tz)).utcoffset().total_seconds()/60)
def main():
    z=zipfile.ZipFile(ROOT/'raw/public/geonames_cities15000.zip')
    gn=[r for r in csv.reader(io.StringIO(z.read('cities15000.txt').decode()),delimiter='\t') if r[8]=='RU']
    cities=[]
    for g in gn:
        cities.append(dict(geonames_id=g[0],name=g[1],asciiname=g[2],alternative_names=g[3],latitude_deg=g[4],longitude_deg=g[5],
            feature_code=g[7],country_code=g[8],admin1_code=g[10],population_publisher=g[14],iana_timezone=g[17],last_modified=g[18],
            value_status='OBSERVED',population_limit='Directory population without common reference year; not used in demand model',source_id='geonames_cities15000'))
    emit(N/'geonames_cities_ru.csv',cities)
    tp=json.loads((ROOT/'raw/public/travelpayouts_cities.json').read_text())
    tp_rows=[dict(travel_city_id='TP-CITY:'+r['code'],code=r['code'],city=r['name'],
        latitude_deg=r['coordinates']['lat'],longitude_deg=r['coordinates']['lon'],
        iana_timezone=r.get('time_zone',''),timezone_null_reason='',source_id='travelpayouts_cities')
        for r in tp if r['country_code']=='RU']
    comparison=[];updated={}
    for filename,idfield in [('airport_version.csv','airport_id'),('city_version.csv','area_id'),('travel_city_version.csv','travel_city_id')]:
        rows=tp_rows if idfield=='travel_city_id' else read(N/filename)
        for r in rows:
            published=r.get('published_iana_timezone',r['iana_timezone'])
            nearest=min((hav(r['latitude_deg'],r['longitude_deg'],g[4],g[5]),g) for g in gn)
            km,g=nearest
            usable=published
            if km>75:status='NO_LOCAL_INDEPENDENT_CROSSCHECK'
            elif not published:status='PUBLISHED_TIMEZONE_MISSING'
            elif offset(published)!=offset(g[17]):
                status='OFFSET_CONFLICT_REQUIRES_REVIEW';usable=''
            elif published!=g[17]:status='OFFSET_AGREES_ZONE_NAME_DIFFERS'
            else:status='PUBLISHED_ZONE_CORROBORATED_BY_NEARBY_CITY'
            r['published_iana_timezone']=published
            r['iana_timezone']=usable
            r['timezone_validation_status']=status
            if status=='OFFSET_CONFLICT_REQUIRES_REVIEW':r['timezone_null_reason']=status
            comparison.append(dict(entity_type='airport' if idfield=='airport_id' else ('travel_city' if idfield=='travel_city_id' else 'city'),entity_id=r[idfield],
                iata_or_name=r.get('iata_code',r.get('city','')),published_iana_timezone=published,published_offset_minutes=offset(published) if published else '',
                nearest_geonames_id=g[0],nearest_city=g[1],nearest_city_distance_km=round(km,3),geonames_iana_timezone=g[17],geonames_offset_minutes=offset(g[17]),
                crosscheck_status=status,usable_iana_timezone=usable,
                limitation='Nearby-city check only, not timezone boundary proof; no spatial imputation when missing',source_ids='ourairports_airports;travelpayouts_airports;travelpayouts_cities;geonames_cities15000;iana_zone1970'))
            updated[r[idfield]]=r
        emit(N/filename,rows)
    emit(N/'timezone_crosscheck.csv',comparison)
    keys=read(ROOT/'canonical_keys.csv')
    for k in keys:
        k['timezone_validation_status']='UNKNOWN'
        if k['canonical_id'] in updated:
            r=updated[k['canonical_id']];k['iana_timezone']=r['iana_timezone']
            k['timezone_validation_status']=r['timezone_validation_status']
            note='; timezone offset conflict retained in diagnostics; usable timezone NULL'
            if r['timezone_validation_status']=='OFFSET_CONFLICT_REQUIRES_REVIEW' and note not in k['limitations']:k['limitations']+=note
    emit(ROOT/'canonical_keys.csv',keys);emit(N/'canonical_keys.csv',keys)
    join=read(N/'airport_timezone_join.csv')
    for r in join:
        checked=updated[r['airport_id']]
        r['published_iana_timezone']=checked['published_iana_timezone']
        r['iana_timezone']=checked['iana_timezone']
        r['timezone_null_reason']=checked['timezone_null_reason']
        r['timezone_validation_status']=checked['timezone_validation_status']
    emit(N/'airport_timezone_join.csv',join)
    checks=dict(created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),version='timezone-check-v1',
        geonames_ru_rows=len(gn),local_TZPATH=list(TZPATH),offset_reference_local_date='2026-12-07',
        conflict_rows=[r for r in comparison if r['crosscheck_status']=='OFFSET_CONFLICT_REQUIRES_REVIEW'],
        limits='Source assertion corroboration and conflict triage; no accepted timezone boundary reconstruction',
        iana_tomsk_reference='raw/public/iana_zone1970.tab: RU Asia/Tomsk MSK+04; raw/public/iana_europe.txt contains 2016 transition and government reference')
    (ROOT/'diagnostics/timezone_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(geonames_ru=len(gn),conflicts=len(checks['conflict_rows']),conflict_entities=[r['entity_id'] for r in checks['conflict_rows']]),ensure_ascii=False))
if __name__=='__main__':main()
