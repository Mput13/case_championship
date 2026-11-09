#!/usr/bin/env python3
"""Independent offline reconciliation of alternative NOAA snapshots; no source code imports."""
import argparse
import calendar
import collections
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import math
from pathlib import Path

OUT=Path(__file__).resolve().parents[1]
DEFAULT_SOURCE=Path('/Users/a/.t3/worktrees/case_championship/research-case5-raw-alternative-20261109/context/16_agent_research/alternative')
YEAR=2024

def digest(b):return hashlib.sha256(b).hexdigest()
def csvbytes(b):return list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
def n(row,key):return float(row[key]) if row.get(key) not in ('',None) else None
def distance(a,b):
    lat1,lon1,lat2,lon2=map(math.radians,[float(a['LAT']),float(a['LON']),float(b['latitude_deg']),float(b['longitude_deg'])])
    q=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 12742*math.asin(min(1,math.sqrt(q)))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=DEFAULT_SOURCE);args=parser.parse_args();root=args.source
    paths=['collectors/weather.py','collectors/join_demo.py','normalized/weather_station_selection.csv','normalized/weather_monthly_2024.csv',
       'normalized/weather_coverage_2024.csv','normalized/weather_validation.json','normalized/join_airport_station_mapping.csv',
       'normalized/join_airport_weather_month.csv','normalized/join_validation.json','raw/noaa_lite_format.txt','raw/noaa_isd_history.csv',
       'raw/noaa_service_notice.html','raw/weather/acquisition_receipts.json','raw/ordinary_airports.source.json','progress.md','headers_policy.json']
    blobs={};manifest=[]
    for name in paths:
        p=root/name
        if not p.exists():manifest.append({'relative_path':name,'status':'ABSENT_AT_SNAPSHOT'});continue
        b=p.read_bytes();blobs[name]=b;dest=OUT/'inputs'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
        manifest.append({'relative_path':name,'source_absolute_path':str(p),'sha256':digest(b),'bytes':len(b),'status':'SNAPSHOTTED'})
    selected=csvbytes(blobs['normalized/weather_station_selection.csv']);history=csvbytes(blobs['raw/noaa_isd_history.csv'])
    expected=[r for r in history if r['CTRY']=='RS' and r['ICAO'] and r['BEGIN']<='20240101' and r['END']>='20241231']
    identity=lambda r:(r['USAF'],r['WBAN'],r['ICAO'])
    assert set(map(identity,selected))==set(map(identity,expected))
    selected_counts={'selected':len(selected),'expected_by_documented_rule':len(expected),
        'unique_station_ids':len({(r['USAF'],r['WBAN'])for r in selected}),'unique_icao':len({r['ICAO']for r in selected})}
    receipts=json.loads(blobs['raw/weather/acquisition_receipts.json']);receipt_by_id={r['dataset_id']:r for r in receipts}
    monthly=csvbytes(blobs['normalized/weather_monthly_2024.csv']);coverage=csvbytes(blobs['normalized/weather_coverage_2024.csv'])
    coverage_by_id={r['station_id']:r for r in coverage};monthly_by_id={(r['station_id'],r['month']):r for r in monthly}
    assert len(monthly_by_id)==len(monthly)
    raw_metadata=[];station_stats=[];mismatches=[];out_of_year=[];all_keys_duplicates=0;computed_months=[]
    for station in selected:
        sid=f"{station['USAF']}-{station['WBAN']}";receipt=receipt_by_id['noaa_lite_'+sid+'-2024']
        if receipt['acquisition_status']!='ACQUIRED_RAW':
            station_stats.append({'station_id':sid,'icao':station['ICAO'],'status':receipt['acquisition_status'],'error':receipt.get('error'),'observed_hours':None,'calendar_hours':8784,'coverage_fraction':None});continue
        raw=root/receipt['raw_path'];b=raw.read_bytes();data=gzip.decompress(b);comp=digest(b);uncomp=digest(data)
        assert comp==receipt['sha256'];assert uncomp==receipt['uncompressed_sha256']
        raw_metadata.append({'source_absolute_path':str(raw),'raw_path':receipt['raw_path'],'source_url':receipt['source_url'],'compressed_sha256':comp,
            'uncompressed_sha256':uncomp,'compressed_bytes':len(b),'uncompressed_bytes':len(data),'retrieved_at_utc':receipt['retrieved_at_utc']})
        bymonth=collections.defaultdict(list);keys=set();duplicate=0;years=collections.Counter()
        for i,line in enumerate(data.decode('ascii').splitlines(),1):
            v=list(map(int,line.split()));assert len(v)==12,(sid,i,len(v))
            timestamp=dt.datetime(*v[:4]);key=tuple(v[:4]);years[v[0]]+=1
            if key in keys:duplicate+=1
            keys.add(key);bymonth[v[1]].append(v)
            if v[0]!=YEAR:out_of_year.append({'station_id':sid,'line':i,'year':v[0]})
        all_keys_duplicates+=duplicate
        cv=coverage_by_id[sid]
        for key,value in {'archive_rows':len(keys),'months_with_records':sum(bool(v)for v in bymonth.values()),'observed_days':len({k[:3]for k in keys}),'calendar_days':366}.items():
            if int(cv[key])!=value:mismatches.append({'station_id':sid,'field':key,'actual':cv[key],'computed':value})
        assert len(data.splitlines())==receipt['record_count']
        temp_total=wind_total=0
        for m in range(1,13):
            obs=bymonth[m];t=[v[4]/10 for v in obs if v[4]!=-9999];w=[v[8]/10 for v in obs if v[8]!=-9999];temp_total+=len(t);wind_total+=len(w)
            days=calendar.monthrange(YEAR,m)[1];key=(sid,f'2024-{m:02d}');r=monthly_by_id[key]
            result={'observed_hours':len(obs),'calendar_hours':days*24,'observed_days':len({v[2]for v in obs}),'calendar_days':days,
                'temperature_observations':len(t),'wind_observations':len(w),'temperature_mean_c':round(sum(t)/len(t),3)if t else None,
                'temperature_min_c':min(t)if t else None,'temperature_below_minus20_count':sum(x< -20 for x in t)if t else None,
                'wind_ge12_ms_count':sum(x>=12 for x in w)if w else None,'wind_max_ms':max(w)if w else None}
            for field,value in result.items():
                if n(r,field)!=value:mismatches.append({'station_id':sid,'month':m,'field':field,'actual':r.get(field),'computed':value})
            computed_months.append({'station_id':sid,'icao':station['ICAO'],'month':f'2024-{m:02d}',**result,
                'observed_hour_fraction':len(obs)/(days*24),'temperature_coverage_fraction':len(t)/(days*24),'wind_coverage_fraction':len(w)/(days*24)})
        station_stats.append({'station_id':sid,'icao':station['ICAO'],'status':'ACQUIRED_RAW_AND_RECONCILED','observed_hours':len(keys),'calendar_hours':8784,
            'coverage_fraction':len(keys)/8784,'observed_days':len({k[:3]for k in keys}),'temperature_observations':temp_total,'wind_observations':wind_total,
            'duplicate_hours':duplicate,'years':dict(years),'first_utc_like_hour':min(keys),'last_utc_like_hour':max(keys)})
    # Independently reproduce the exact-ICAO and coordinate join, keeping source limitations explicit.
    source=json.loads(blobs['raw/ordinary_airports.source.json']);airport_raw=(root/source['raw_path']).read_bytes()
    assert digest(airport_raw)==source['compressed_sha256'];airport_bytes=gzip.decompress(airport_raw);assert digest(airport_bytes)==source['sha256']
    airports=csvbytes(airport_bytes);airport_index=collections.defaultdict(list)
    for a in airports:
        if a['iso_country']=='RU' and a['icao_code']:airport_index[a['icao_code']].append(a)
    mappings=csvbytes(blobs['normalized/join_airport_station_mapping.csv']);joined=csvbytes(blobs['normalized/join_airport_weather_month.csv'])
    station_index={r['ICAO']:r for r in selected};mapping_by_icao={r['icao']:r for r in mappings}
    assert len(mapping_by_icao)==len(mappings)
    distances=[];unmatched=[];distance_errors=[]
    for row in mappings:
        matches=airport_index[row['icao']]
        if len(matches)==1:
            a=matches[0];d=distance(station_index[row['icao']],a);status='EXACT_ICAO_COORD_WITHIN25KM'if d<=25 else'EXACT_ICAO_COORD_GT25KM_REVIEW'
            if row['airport_id']!=a['id'] or row['mapping_status']!=status or abs(float(row['station_airport_distance_km'])-d)>0.00051:distance_errors.append({'icao':row['icao'],'computed_km':d,'reported':row['station_airport_distance_km'],'status':status})
            distances.append({'icao':row['icao'],'station_id':row['station_id'],'iata':row['iata'],'distance_km':round(d,3),'status':status,'airport_id':a['id'],'airport_type':a['type']})
        else:
            assert not row['airport_id'];unmatched.append({'icao':row['icao'],'station_id':row['station_id'],'matching_airports':len(matches),'status':row['mapping_status']})
    join_key_counts=collections.Counter((r['station_id'],r['weather_month'])for r in joined)
    join_duplicates=[{'key':list(k),'count':v}for k,v in join_key_counts.items()if v>1]
    missing_hour_denominators=[f for f in ['observed_hours','calendar_hours']if f not in joined[0]]
    all_reconciled=not(mismatches or out_of_year or all_keys_duplicates or distance_errors or join_duplicates)
    input_changes=[]
    for record in manifest:
        if record['status']=='SNAPSHOTTED' and digest(Path(record['source_absolute_path']).read_bytes())!=record['sha256']:input_changes.append(record['relative_path'])
    result={'audited_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'ARITHMETIC_AND_JOIN_CHECKS_PASS_WITH_SCOPE_LIMITS'if all_reconciled else'RECONCILIATION_FAILED',
        'source_base':str(root),'selected_rule_check':selected_counts,'receipt_rows':len(receipts),'raw_files_checked':len(raw_metadata),'raw_observations':sum(r['observed_hours']or 0 for r in station_stats),
        'monthly_rows':len(monthly),'calendar_hours_per_full_2024_station':8784,'duplicate_station_hours':all_keys_duplicates,'out_of_year_rows':out_of_year,'mismatches':mismatches,
        'station_stats':station_stats,'coverage_summary':{'observed_hours_fraction_min':min(r['coverage_fraction']for r in station_stats if r['coverage_fraction']is not None),
            'observed_hours_fraction_max':max(r['coverage_fraction']for r in station_stats if r['coverage_fraction']is not None),
            'zero_observation_station_months':sum(r['observed_hours']==0 for r in computed_months),'full_observed_day_but_incomplete_hour_months':sum(r['observed_days']==r['calendar_days']and r['observed_hours']<r['calendar_hours']for r in computed_months)},
        'join':{'station_rows':len(mappings),'joined_month_rows':len(joined),'input_month_rows':len(monthly),'key_duplicates':join_duplicates,'distance_or_identity_errors':distance_errors,
            'mapping_statuses':dict(collections.Counter(r['mapping_status']for r in mappings)),'unmatched':unmatched,'largest_matched_distances':sorted(distances,key=lambda r:-r['distance_km'])[:10],
            'missing_hour_denominators_in_join':missing_hour_denominators,'airport_icao_duplicates':{k:[a['id']for a in v]for k,v in airport_index.items()if len(v)>1}},
        'inputs_changed_during_audit':input_changes,'limitations':['No new source fetch; all83archivedfiles checked against supplied receipts and independently reconciled.',
            'Exact ICAO and distance agreement do not validate2024airport exposure or local representativeness.25km is a screening threshold, not meteorological acceptance.',
            'Selection by station-history endpoints and country/ICAO does not guarantee complete hours, exhaustive airports or unbiased comparison.',
            'Temperature/wind archived observations are not flightloss, present disruption probability, payload/dispatch legality or expected hub loss.',
            '2024one-year archive is a historical baseline, not multi-year climate normal.']}
    (OUT/'reproduction.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (OUT/'input_manifest.json').write_text(json.dumps({'captured_at_utc':result['audited_at_utc'],'source_base':str(root),'snapshots':manifest,'raw_archives':raw_metadata,
        'ordinary_airport_compressed_sha256':source['compressed_sha256'],'ordinary_airport_uncompressed_sha256':source['sha256']},ensure_ascii=False,indent=2)+'\n')
    with(OUT/'recomputed_month_coverage.csv').open('w',newline='')as f:
        writer=csv.DictWriter(f,list(computed_months[0]));writer.writeheader();writer.writerows(computed_months)
    print(json.dumps({k:result[k]for k in ['status','selected_rule_check','raw_files_checked','raw_observations','monthly_rows','duplicate_station_hours','coverage_summary','join','inputs_changed_during_audit']},ensure_ascii=False))

if __name__=='__main__':main()
