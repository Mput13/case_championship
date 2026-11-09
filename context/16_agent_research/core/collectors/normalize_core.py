#!/usr/bin/env python3
"""Offline normalization, exact-key joins, and diagnostics for acquired directories.

No catchment, demand, ranking, aircraft range or missing-value imputation is applied.
City/airport links from coordinates are candidates, not accepted administrative links.
"""
import collections
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re
import zipfile
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"normalized"
VERSION="core-normalize-v1"
NOW=dt.datetime.now(dt.timezone.utc).isoformat()

def digest(b):return hashlib.sha256(b).hexdigest()
def emit(name, rows, fields=None, packed=False):
    rows=list(rows)
    fields=fields or (list(rows[0]) if rows else [])
    s=io.StringIO(newline="");w=csv.DictWriter(s,fieldnames=fields);w.writeheader();w.writerows(rows)
    b=s.getvalue().encode();p=OUT/name
    if packed:p=p.with_suffix(p.suffix+".gz");p.write_bytes(gzip.compress(b,mtime=0))
    else:p.write_bytes(b)
    return dict(path=str(p.relative_to(ROOT)),record_count=len(rows),sha256=digest(b),stored_sha256=digest(p.read_bytes()),size_bytes=len(b),compression="gzip" if packed else "none")

def norm_name(s):return re.sub(r"[^а-яa-z0-9]","",s.lower().replace("ё","е"))
def hav(a,b,c,d):
    a,b,c,d=map(math.radians,(float(a),float(b),float(c),float(d)))
    return 6371*2*math.asin(min(1,math.sqrt(math.sin((c-a)/2)**2+math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2)))

def unique(rows,key):
    c=collections.Counter(key(r) for r in rows)
    return dict(rows=len(rows),distinct_keys=len(c),duplicated_keys=[str(k) for k,v in c.items() if v>1][:30],extra_rows=sum(v-1 for v in c.values()))

def main():
    OUT.mkdir(exist_ok=True)
    manifest=json.loads((ROOT/"acquisition_manifest.json").read_text())
    inputs={e['dataset_id']:e for e in manifest['datasets'] if e['acquisition_status']!='ACCESS_FAILED'}
    def raw(id):
        e=inputs[id];b=(ROOT/e['raw_path']).read_bytes()
        if e['compression']=='gzip':b=gzip.decompress(b)
        assert digest(b)==e['sha256'],id
        return b
    a=list(csv.DictReader(io.StringIO(raw('ourairports_airports').decode('utf-8-sig'))))
    runway=list(csv.DictReader(io.StringIO(raw('ourairports_runways').decode('utf-8-sig'))))
    tp=json.loads(raw('travelpayouts_airports'));tc=json.loads(raw('travelpayouts_cities'))
    z=zipfile.ZipFile(io.BytesIO(raw('tochno_intercity_zip')))
    member='data_intercity_connectivity_162_v20260629.csv';b=z.read(member)
    t=list(csv.DictReader(io.StringIO(b.decode('utf-8-sig')),delimiter=';'))
    assert len(t)==180*179*3
    # The archive is raw, not an independently audited timetable.
    checks={'created_at_utc':NOW,'version':VERSION,'input_hashes_verified':len(inputs),
            'tochno_member':dict(path=member,sha256=digest(b),size_bytes=len(b),rows=len(t)),
            'keys':{},'limitations':['Tochno reverse direction copies original; not independent evidence',
                'All Tochno durations are provider MODEL_ESTIMATE; no scheduled travel-date observation',
                'OurAirports ISO scope retained; no attempt to redefine borders or airport operating authority',
                'Timezone is published Travelpayouts field checked against local IANA database; not statutory boundary verification']}
    ru=[r for r in a if r['iso_country']=='RU']
    rt=[r for r in tp if r['country_code']=='RU' and r['iata_type']=='airport']
    checks['keys']['ourairports_ru_id']=unique(ru,lambda r:r['id'])
    checks['keys']['ourairports_ru_iata_nonempty']=unique([r for r in ru if r['iata_code']],lambda r:r['iata_code'])
    checks['keys']['travelpayouts_ru_airport_code']=unique(rt,lambda r:r['code'])
    checks['keys']['tochno_pair_mode']=unique(t,lambda r:(r['oktmo_from'],r['oktmo_to'],r['transport_type']))
    for label,v in checks['keys'].items():
        if v['extra_rows']:raise ValueError('Unexpected duplicate key '+label)
    tpby={r['code']:r for r in rt};apids={r['id'] for r in ru};tcby={r['code']:r for r in tc if r['country_code']=='RU'}
    airports=[];join=[];keys=[]
    for r in ru:
        f=tpby.get(r['iata_code']) if r['iata_code'] else None
        tz=(f.get('time_zone') or '') if f else ''
        tz_valid=False
        if tz:
            try:ZoneInfo(tz);tz_valid=True
            except ZoneInfoNotFoundError:pass
        diff=hav(r['latitude_deg'],r['longitude_deg'],f['coordinates']['lat'],f['coordinates']['lon']) if f else None
        status='MATCHED_CODE' if f else ('NO_IATA' if not r['iata_code'] else 'UNMATCHED_CODE')
        rec=dict(airport_id='OA:'+r['id'],ourairports_id=r['id'],ident=r['ident'],icao_code=r.get('icao_code',''),
            iata_code=r['iata_code'],local_code=r['local_code'],name=r['name'],municipality=r['municipality'],
            iso_region=r['iso_region'],region_id='ISO3166-2:'+r['iso_region'],iso_country=r['iso_country'],type=r['type'],
            latitude_deg=r['latitude_deg'],longitude_deg=r['longitude_deg'],elevation_ft=r['elevation_ft'],scheduled_service=r['scheduled_service'],
            travel_city_code=f['city_code'] if f else '',travel_city_name=tcby.get(f['city_code'],{}).get('name','') if f else '',
            iana_timezone=tz if tz_valid else '',timezone_source='travelpayouts_airports' if tz_valid else '',
            timezone_null_reason='' if tz_valid else ('INVALID_IANA' if tz else status),
            coordinate_difference_km=round(diff,3) if diff is not None else '',
            join_status=status,geographic_review='COORDINATES_DIFFER_OVER_10KM' if diff is not None and diff>10 else '',
            valid_from='',valid_to='',validity_reason='Source does not provide validity interval; snapshot only',snapshot_at_utc=inputs['ourairports_airports']['retrieved_at_utc'],
            value_status='OBSERVED',observation_scope='Publisher directory assertion; not verified operational status',source_id='ourairports_airports')
        airports.append(rec)
        if r['iata_code']:
            join.append({k:rec[k] for k in ['airport_id','ident','iata_code','name','join_status','iana_timezone','timezone_null_reason','coordinate_difference_km','geographic_review']})
        keys.append(dict(entity_type='airport',canonical_id=rec['airport_id'],source_system='OurAirports',source_key=r['id'],
            name=r['name'],parent_id=rec['region_id'],iata=r['iata_code'],icao_or_ident=r['ident'],oktmo='',iana_timezone=rec['iana_timezone'],
            relation='identity',valid_from='',valid_to='',snapshot_at_utc=rec['snapshot_at_utc'],limitations='id stable within source; ident may change; directory not state register'))
    rrun=[r for r in runway if r['airport_ref'] in apids]
    rr=[]
    for r in rrun:
        rr.append(dict(runway_id='OA-RWY:'+r['id'],airport_id='OA:'+r['airport_ref'],airport_ident=r['airport_ident'],length_ft=r['length_ft'],
            length_m=round(float(r['length_ft'])*0.3048,3) if r['length_ft'] else '',width_ft=r['width_ft'],surface=r['surface'],lighted=r['lighted'],closed=r['closed'],
            le_ident=r['le_ident'],he_ident=r['he_ident'],value_status='DERIVED',method='feet x 0.3048 exact conversion; other fields publisher assertions',source_id='ourairports_runways'))
    cities={};inconsistencies=[]
    attrs=['city','region','oktmo','sber_territory_id','is_capital','population','lat','lon']
    for r in t:
        for side in ['from','to']:
            c={k:r[k+'_'+side] for k in attrs};key=c['oktmo']
            if key in cities and cities[key]!=c:inconsistencies.append(dict(oktmo=key,old=cities[key],new=c))
            cities[key]=c
    assert len(cities)==180 and not inconsistencies
    cityrows=[];links=[]
    for k,c in sorted(cities.items()):
        matches=[]
        # Direct city identity only when names and coordinates agree; no nearest-town assignment.
        for v in tcby.values():
            if norm_name(v['name'])==norm_name(c['city']):
                km=hav(c['lat'],c['lon'],v['coordinates']['lat'],v['coordinates']['lon'])
                if km<30:matches.append((km,v))
        matches.sort(key=lambda x:x[0]);v=matches[0][1] if len(matches)==1 else None
        tz=v.get('time_zone','') if v else ''
        crow=dict(area_id='OKTMO:'+k,oktmo=k,city=c['city'],region=c['region'],latitude_deg=c['lat'],longitude_deg=c['lon'],
            population_persons_2021=c['population'],population_status='OBSERVED',population_scope='2021 census city population reported by Tochno; primary table not rechecked',
            sber_territory_id=c['sber_territory_id'],is_regional_capital=c['is_capital'],travel_city_code=v['code'] if v else '',
            iana_timezone=tz,timezone_null_reason='' if tz else ('NO_UNIQUE_CITY_MATCH' if matches else 'NO_CITY_MATCH'),
            source_id='tochno_intercity_zip',snapshot_at_utc=inputs['tochno_intercity_zip']['retrieved_at_utc'],valid_from='',valid_to='',validity_reason='OKTMO source version 20260629, boundaries not independently version-verified')
        cityrows.append(crow)
        keys.append(dict(entity_type='city',canonical_id=crow['area_id'],source_system='OKTMO as published by Tochno',source_key=k,name=c['city'],parent_id='',
            iata=v['code'] if v else '',icao_or_ident='',oktmo=k,iana_timezone=tz,relation='settlement city, not aggregate catchment',valid_from='',valid_to='',
            snapshot_at_utc=crow['snapshot_at_utc'],limitations='Census 2021 population; OKTMO boundaries/version need review before current municipality join'))
        for ar in airports:
            if ar['type'] in ['large_airport','medium_airport','small_airport'] and ar['iata_code']:
                km=hav(c['lat'],c['lon'],ar['latitude_deg'],ar['longitude_deg'])
                if km<=75:
                    links.append(dict(area_id=crow['area_id'],city=c['city'],airport_id=ar['airport_id'],iata=ar['iata_code'],airport_name=ar['name'],
                        distance_greatcircle_km=round(km,3),link_status='CANDIDATE_GEOGRAPHIC_LINK',value_status='DERIVED',
                        method='haversine city center to airport <=75km; all candidates retained, no catchment allocation',limitations='Not driving time or proof of access; overlap must not be summed',source_ids='tochno_intercity_zip;ourairports_airports'))
    access=[];present_by_mode=collections.Counter();missing=collections.Counter();src=collections.Counter();reverse_mismatch=0
    pairmap={(r['oktmo_from'],r['oktmo_to'],r['transport_type']):r for r in t}
    for n,r in enumerate(t,start=2):
        present=bool(r['distance_km']);present_by_mode[r['transport_type']]+=present
        missing[(r['transport_type'],r['missing_reason'])]+=1;src[(r['transport_type'],r['source'])]+=1
        rev=pairmap[(r['oktmo_to'],r['oktmo_from'],r['transport_type'])]
        if any(r[c]!=rev[c] for c in ['distance_hr','distance_km','source']):reverse_mismatch+=1
        access.append(dict(origin_area_id='OKTMO:'+r['oktmo_from'],destination_area_id='OKTMO:'+r['oktmo_to'],mode=r['transport_type'],
            distance_km=r['distance_km'],distance_hr=r['distance_hr'],distance_status='DERIVED' if r['transport_type'] in ['air','rail'] and present else 'MODEL_ESTIMATE' if present else 'UNKNOWN',
            duration_status='MODEL_ESTIMATE' if r['distance_hr'] else 'UNKNOWN',provider_route_assertion='PRESENT_IN_DATASET' if present else 'NOT_FOUND_BY_PROVIDER',
            missing_reason='' if r['missing_reason']=='CD' else r['missing_reason'],underlying_source='' if r['source']=='ND' else r['source'],
            comment='' if r['comment']=='CD' else r['comment'],travel_date='',temporal_coverage='2026 publisher mixed reference; not matched winter schedule',
            directed_observation_independent='false; reverse copied by publisher',raw_row=n,source_id='tochno_intercity_zip'))
    files=[]
    files.append(emit('airport_version.csv',airports));files.append(emit('runway_version.csv',rr))
    files.append(emit('city_version.csv',cityrows));files.append(emit('access_alternative.csv',access,packed=True))
    files.append(emit('city_airport_candidate_links.csv',links));files.append(emit('airport_timezone_join.csv',join))
    # Include every travel-city identity separately; do not collapse it into an administrative area.
    for c in tcby.values():
        keys.append(dict(entity_type='travel_city',canonical_id='TP-CITY:'+c['code'],source_system='Travelpayouts',source_key=c['code'],name=c['name'],parent_id='ISO3166-1:RU',
            iata=c['code'],icao_or_ident='',oktmo='',iana_timezone=c.get('time_zone',''),relation='travel market; independent from administrative municipality',
            valid_from='',valid_to='',snapshot_at_utc=inputs['travelpayouts_cities']['retrieved_at_utc'],limitations='Codes may change; no boundary or population implied'))
    files.append(emit('canonical_keys.csv',keys))
    # Required top-level location duplicates exact bytes deliberately, with same hash.
    (ROOT/'canonical_keys.csv').write_bytes((OUT/'canonical_keys.csv').read_bytes())
    checks['airport_join']=dict(left_rows=len([r for r in ru if r['iata_code']]),right_ru_airport_rows=len(rt),
        result_rows=len(join),matched=sum(r['join_status']=='MATCHED_CODE' for r in join),unmatched=[r['iata_code'] for r in join if r['join_status']!='MATCHED_CODE'],
        multiplied_rows=0,coordinate_discrepancies_over_10km=[r for r in join if r['geographic_review']])
    checks['coverage']=dict(ourairports_ru=len(ru),ourairports_ru_iata=len(join),runways_ru=len(rr),
        tochno_cities=len(cities),tochno_regions=len({c['region'] for c in cities.values()}),city_timezone_matches=sum(bool(r['iana_timezone']) for r in cityrows),
        travelpayouts_ru_cities=len(tcby),city_airport_candidate_links=len(links),
        transport_rows=len(t),transport_present_by_mode=dict(present_by_mode),transport_null_rows=len(t)-sum(present_by_mode.values()),
        reverse_distance_source_disagreements=reverse_mismatch)
    checks['transport_sources']=[dict(mode=k[0],source=k[1],rows=v) for k,v in sorted(src.items())]
    checks['transport_missing_reasons']=[dict(mode=k[0],reason=k[1],rows=v) for k,v in sorted(missing.items())]
    checks['normalized_files']=files
    (ROOT/'diagnostics'/'normalization_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:checks[k] for k in ['coverage','airport_join']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
