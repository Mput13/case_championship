#!/usr/bin/env python3
"""Bounded offline grain checks and region context from immutable a875cdd.

No geography inferred from ISO, OKTMO prefixes or proximity. No demand model.
Only this script's own output directory is written. All numeric units stay native.
"""
import collections
import csv
import datetime as dt
from decimal import Decimal
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

OUT=Path(__file__).resolve().parent
REPO=OUT.parents[4]
BASE='context/16_agent_research/core/'
SOC=BASE+'branches/social_economy/'
SHA='a875cdd1ecaf778f53ba06cab1c66581a7f215c6'
VERSION='social-integration-v1.1'
GATEWAYS=['KVX','MRV','NJC','UFA','SVX','OMS','KJA']
TOP='Муниципальное образование верхнего уровня'
SELECT={
 'Y477110191':('DESTINATION_ACCOMMODATION','Reported persons accommodated; not OD or unique regional visitors'),
 'Y477110192':('DESTINATION_ESTABLISHMENTS','Number of establishments is not beds, occupancy, nights or available capacity; source unit missing'),
 'Y477110404':('ORIGIN_AGENCY_SUPPLY','Agency count is not travellers or attraction of this destination; source unit missing'),
 'Y477110405':('ORIGIN_AGENCY_PRODUCTS','Tour packages sold by regional firms; destination/transport not resolved'),
 'Y477110479':('ORIGIN_AGENCY_OUTBOUND_FOREIGN','Residents served by agencies for foreign tours; not arrivals into this region'),
 'Y477110480':('ORIGIN_AGENCY_OUTBOUND_DOMESTIC','Agency-reported domestic tour clients; destinations/transport unknown'),
}
inputs=[]
def digest(b):return hashlib.sha256(b).hexdigest()
def frozen(path):
    b=subprocess.check_output(['git','show',SHA+':'+path],cwd=REPO)
    inputs.append(dict(path=path,git_sha=SHA,sha256=digest(b),size_bytes=len(b),source='PINNED_GIT_BLOB'))
    return b
def csvrows(path):
    b=frozen(path)
    if path.endswith('.gz'):b=gzip.decompress(b)
    return list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
def save(name,rows,fields=None):
    with (OUT/name).open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def dump(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def mkey(r):return tuple(r[k] for k in ['region_id','oktmo','mun_level','year'])
def parse_raw_zip(meta):
    path=REPO/SOC/meta['raw_path'];b=path.read_bytes()
    assert digest(b)==meta['sha256'],meta['dataset_id']
    inputs.append(dict(path=SOC+meta['raw_path'],git_sha=SHA,sha256=digest(b),size_bytes=len(b),source='RETAINED_LOCAL_RAW_VERIFIED_AGAINST_PINNED_MANIFEST',source_url=meta['source_url']))
    rows=collections.defaultdict(list)
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        member=next(n for n in z.namelist() if n.endswith('.csv'))
        with io.TextIOWrapper(z.open(member),encoding='utf-8-sig') as h:
            for no,r in enumerate(csv.DictReader(h,delimiter=';'),2):
                if r['year']=='2024' and r['mun_level']==TOP:
                    r['source_row']=str(no);r['source_archive_member']=member;rows[mkey(r)].append(r)
    return rows
def main():
    manifest=json.loads(frozen(SOC+'dataset_manifest.json'));byid={e['dataset_id']:e for e in manifest['datasets']}
    clean=csvrows(SOC+'normalized/example_join_municipal_2024.csv')
    previous_rejected=csvrows(SOC+'normalized/example_join_municipal_2024_rejected.csv')
    wage=parse_raw_zip(byid['tochno_bdmo_municipal_wages'])
    pop=parse_raw_zip(byid['tochno_bdmo_municipal_population'])
    result={};held=[];label_mismatches=[]
    for k,ws in wage.items():
        ps=pop.get(k,[]);reason=''
        if len(ws)!=1 or len(ps)!=1:reason='NO_POPULATION_MATCH' if not ps else 'AMBIGUOUS_KEY'
        elif ws[0]['mun_type']!=ps[0]['mun_type']:reason='MUNICIPAL_TYPE_MISMATCH_REQUIRES_REVIEW'
        if reason:
            held.append(dict(record_class='HELD_WAGE_LEFT_JOIN',region_id=k[0],oktmo=k[1],mun_level=k[2],year=k[3],wage_records=len(ws),population_records=len(ps),reason=reason,acceptance='QUARANTINE'));continue
        w,p=ws[0],ps[0];result[k]=(w,p)
        if w['municipality']!=p['municipality'] or w['mun_district']!=p['mun_district']:label_mismatches.append(k)
    cleanby={mkey(r):r for r in clean}
    assert len(cleanby)==len(clean)==2022
    assert set(cleanby)==set(result)
    assert len(held)==277
    expected={(r['region_id'],r['oktmo'],r['year'],r['reason']) for r in previous_rejected}
    assert expected=={(r['region_id'],r['oktmo'],r['year'],r['reason']) for r in held}
    trace=[];comparisons=0
    for k,(w,p) in result.items():
        c=cleanby[k]
        assert w['source_row']==c['wage_source_row'] and p['source_row']==c['population_source_row']
        assert Decimal(w['indicator_value'])==Decimal(c['gross_monthly_wage_rub'])
        assert Decimal(p['indicator_value'])==Decimal(c['annual_average_population_persons'])
        assert w['indicator_period']=='Январь-декабрь'
        assert w['indicator_unit']=='Рубль' and p['indicator_unit']=='Человек'
        comparisons+=2
    for k in [sorted(result)[i] for i in [0,len(result)//2,-1]]:
        w,p=result[k];trace.append(dict(region_id=k[0],oktmo=k[1],year=k[3],wage_source_row=w['source_row'],population_source_row=p['source_row'],gross_monthly_wage_rub=w['indicator_value'],annual_average_population_persons=p['indicator_value']))
    population_only=[]
    for k in sorted(set(pop)-set(wage)):
        population_only.append(dict(record_class='POPULATION_ONLY_COVERAGE',region_id=k[0],oktmo=k[1],mun_level=k[2],year=k[3],wage_records=0,population_records=len(pop[k]),reason='OUTSIDE_WAGE_LEFT_JOIN; wage observation absent, not zero',acceptance='UNKNOWN_WAGE_NOT_JOINED'))
    save('municipal_quarantine.csv',sorted(held+population_only,key=lambda r:(r['record_class'],r['region_id'],r['oktmo'])))
    validation=dict(version=VERSION,frozen_sha=SHA,year=2024,grain='upper-level municipality x year; not city/catchment',
        raw_wage_rows=sum(map(len,wage.values())),raw_wage_unique_keys=len(wage),raw_population_rows=sum(map(len,pop.values())),raw_population_unique_keys=len(pop),
        clean_join_keys=len(result),held_wage_left_keys=len(held),population_only_keys=len(population_only),
        held_reason_counts=dict(collections.Counter(r['reason'] for r in held)),numeric_cell_comparisons_to_raw=comparisons,
        numeric_cell_mismatches=0,municipality_label_mismatches=len(label_mismatches),source_rows_match=True,
        trace_sample=trace,aggregation='NONE; lower/upper/subject levels never added; population is not a wage weight',
        acceptance='RAW_CELL_AND_SOURCE_KEY_CHECKS_PASS; city/catchment boundaries NOT_VALIDATED',all_checks_pass=True)
    dump('municipal_join_validation.json',validation)

    airports=csvrows(BASE+'normalized/airport_version.csv');cities=csvrows(BASE+'normalized/city_version.csv')
    cross=csvrows(SOC+'normalized/region_crosswalk.csv')
    census=csvrows(BASE+'normalized/large_exports/social_economy__census_2021_settlement_partitions.csv.gz')
    tourism=csvrows(SOC+'normalized/tochno_regions_tourism.csv.gz')
    ap={r['iata_code']:r for r in airports if r['iata_code'] in GATEWAYS}
    cr=collections.defaultdict(list)
    for r in cross:
        for name in {r['census_region_label'],r['regional_table_label']}:cr[name].append(r)
    gateways=[]
    for code in GATEWAYS:
        a=ap[code];matches=[r for r in cities if r['travel_city_code']==code]
        assert not a['geographic_review'], 'Airport identity/coordinate review is not bypassed'
        if len(matches)==1:
            city=matches[0];name=city['city'];reg=city['region'];source=BASE+'normalized/city_version.csv';sid=city['area_id'];basis='TP travel-city code to unique source city; explicit source region label'
        elif code=='MRV':
            matches=[r for r in census if r['settlement_name']=='г. Минеральные Воды']
            assert len(matches)==1
            city=matches[0];name='Минеральные Воды';reg=city['region'];source=BASE+'normalized/large_exports/social_economy__census_2021_settlement_partitions.csv.gz';sid='CENSUS-SOURCE-ROW:'+city['source_row'];basis='Exact explicit settlement label and source region; no geocoded ISO/OKTMO/coordinates used'
        else:raise ValueError('No unambiguous source-city label for '+code)
        assert name==a['travel_city_name'], 'Published airport market label must agree with source-city label'
        regrows=cr[reg];assert len(regrows)==1,reg
        r=regrows[0]
        gateways.append(dict(airport_iata=code,airport_id=a['airport_id'],airport_version_sha=SHA,travel_city_code=a['travel_city_code'],city_name=name,
            source_city_id=sid,city_input_path=source,source_region_label=reg,canonical_region_id=r['canonical_area_id'],regional_table_label=r['regional_table_label'],
            regional_oktmo=r['regional_oktmo'],mapping_method=basis,geography_rule=r['geographic_rule'],
            raw_census_iso_used=False,municipal_boundary_join_status='UNKNOWN_NOT_ATTEMPTED; no OKTMO prefix stripping',
            mapping_value_status='DERIVED',acceptance='REGION_CONTEXT_ONLY; no catchment/population allocation'))
    save('gateway_region_crosswalk.csv',gateways)
    indicators=collections.defaultdict(list)
    for r in tourism:indicators[r['indicator_code']].append(r)
    selection=[]
    for code,rr in sorted(indicators.items()):
        role,limit=SELECT.get(code,('EXCLUDED_CULTURE_SPORT_OR_SUMMER_CHILD_CONTEXT','Not selected for these winter passenger products; no numeric demand uplift'))
        selection.append(dict(indicator_code=code,indicator_name=rr[0]['indicator_name'],selected=code in SELECT,context_role=role,
            native_units=' | '.join(sorted({r['indicator_unit'] or 'UNKNOWN_PUBLISHER_UNIT_MISSING' for r in rr})),
            last_year=max(r['year'] for r in rr),limit=limit,source_section=rr[0]['section'],frozen_sha=SHA))
    save('tourism_indicator_selection.csv',selection)
    contexts=[];coverage=[]
    for g in gateways:
        for code,(role,limit) in SELECT.items():
            rr=[r for r in tourism if r['indicator_code']==code and r['object_name']==g['regional_table_label'] and r['object_level']=='Регион' and r['year']=='2024']
            status='MATCHED_UNIQUE' if len(rr)==1 else 'NO_2024_OBSERVATION' if not rr else 'QUARANTINE_MULTIPLE_EDITIONS'
            r=rr[0] if len(rr)==1 else {}
            contexts.append(dict(airport_iata=g['airport_iata'],canonical_region_id=g['canonical_region_id'],region_name=g['regional_table_label'],
                indicator_code=code,indicator_name=(r or indicators[code][0])['indicator_name'],year=2024,
                value=r.get('indicator_value',''),unit_native=r.get('indicator_unit',''),unit_missing_reason=r.get('unit_missing_reason','NO_UNIQUE_OBSERVATION' if not r else ''),
                value_status=r.get('value_status','UNKNOWN'),value_missing_reason=r.get('value_missing_reason','NO_UNIQUE_OBSERVATION' if not r else ''),
                source_edition=r.get('source',''),publisher_version=r.get('version_date',''),source_dataset_id='tochno_regions_tourism',source_row=r.get('source_row',''),
                source_input_path=SOC+'normalized/tochno_regions_tourism.csv.gz',source_git_sha=SHA,context_role=role,join_status=status,
                acceptance=('REGIONAL_ANNUAL_CONTEXT_ONLY' if r.get('indicator_unit') else 'QUARANTINE_UNIT_UNKNOWN') if status=='MATCHED_UNIQUE' else 'UNKNOWN_OR_QUARANTINE',
                temporal_limit='Annual2024; December2026 seasonality UNKNOWN',interpretation_limit=limit+'; not gateway-city/OD/route or incremental RW sales'))
    save('gateway_region_context_2024.csv',contexts)
    # Check every context value, source edition, explicit region label and native
    # unit against the original tourism ZIP, independently of normalized joins.
    tm=byid['tochno_regions_tourism'];tb=(REPO/SOC/tm['raw_path']).read_bytes()
    assert digest(tb)==tm['sha256']
    inputs.append(dict(path=SOC+tm['raw_path'],git_sha=SHA,sha256=digest(tb),size_bytes=len(tb),source='RETAINED_RAW_VERIFIED_AGAINST_PINNED_MANIFEST',source_url=tm['source_url']))
    wanted={int(r['source_row']):r for r in contexts};tourism_raw_checks=0
    with zipfile.ZipFile(io.BytesIO(tb)) as z:
        member=next(n for n in z.namelist() if n.endswith('.csv'))
        with io.TextIOWrapper(z.open(member),encoding='utf-8-sig') as h:
            for no,raw in enumerate(csv.DictReader(h,delimiter=';'),2):
                if no not in wanted:continue
                r=wanted[no]
                assert raw['year']=='2024' and raw['object_level']=='Регион'
                assert raw['object_name']==r['region_name'] and raw['indicator_code']==r['indicator_code']
                assert raw['source']==r['source_edition']
                assert Decimal(raw['indicator_value'])==Decimal(r['value'])
                assert ('' if raw['indicator_unit']=='ND' else raw['indicator_unit'])==r['unit_native']
                tourism_raw_checks+=1
    assert tourism_raw_checks==42
    for code in SELECT:
        rr=[r for r in contexts if r['indicator_code']==code]
        coverage.append(dict(table='gateway_region_context_2024',slice=code,expected_keys=7,matched_keys=sum(r['join_status']=='MATCHED_UNIQUE' for r in rr),
            nonnull_values=sum(r['value']!='' for r in rr),known_units=sum(r['unit_native']!='' for r in rr),period='2024 annual',grain='gateway label -> region x indicator x source edition',
            coverage_limit='Seven region mappings do not establish coverage of route OD or winter products'))
    coverage += [dict(table='municipal_join',slice='wage-left 2024',expected_keys=len(wage),matched_keys=len(result),nonnull_values=len(result),known_units=len(result),period='2024 Jan–Dec wage / annual-average population',grain='upper-level municipality x year',coverage_limit='277 held wage-left keys; 286 additional population-only keys are outside wage-left denominator')]
    save('coverage.csv',coverage)
    dictionary=[
      ('gateway_region_crosswalk','airport_iata','gateway travel-market label to source city and explicit region','N/A','a875cdd source labels; not verified catchment/municipal boundary'),
      ('gateway_region_context_2024','airport_iata;indicator_code;year;source_edition','region x indicator x year x source edition (repeated context by gateway)','unit_native per row; NULL retained','Observed regional value joined by DERIVED mapping; annual2024, not OD/seasonality;14unit-unknown claims quarantined from quantitative use'),
      ('tourism_indicator_selection','indicator_code','one original section indicator','native_units per source','Six selected tourism-context indicators; twelve cultural/sport/summer-child indicators excluded'),
      ('municipal_quarantine','record_class;region_id;oktmo;mun_level;year','upper-level municipality x year','wage/population record counts, not zero values','277 held wage-left keys + 286 population-only coverage keys; no imputation'),
      ('municipal_join_validation','year;frozen_sha','validation run over two raw ZIPs and prior joined table','gross nominal monthly wage RUB; annual-average population persons','Wage scope large/medium/nonprofit employers; not all residents income. No totals or population weighting'),
      ('coverage','table;slice','scope-specific coverage denominator','keys/nonnull/unit counts','Completeness separated from attractiveness; no predictive edge claimed'),
    ]
    save('table_dictionary.csv',[dict(zip(['table','key','grain','units','interpretation'],r)) for r in dictionary])
    manifest=dict(version=VERSION,generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),frozen_source_sha=SHA,
        command='python3 '+str((OUT/'build_social.py').relative_to(REPO)),inputs=inputs,
        validation=dict(municipal_raw_numeric_cells=4044,tourism_raw_context_rows=tourism_raw_checks,raw_value_mismatches=0,
            raw_census_iso_used=False,airport_coordinate_hold_bypassed=False,municipal_boundary_or_catchment_join='NOT_RUN'),
        boundaries='Offline source-key/cell/region-context checks only; no new downloads, no model or scenario uplift, no sum of nested territories')
    manifest['outputs']=[dict(path=f.name,sha256=digest(f.read_bytes()),size_bytes=f.stat().st_size) for f in sorted(OUT.iterdir()) if f.is_file() and f.name!='input_manifest.json']
    dump('input_manifest.json',manifest)
    print(json.dumps(dict(version=VERSION,clean_municipal_keys=len(result),held_wage_left=len(held),population_only=len(population_only),raw_numeric_checks=comparisons,gateway_regions=len(gateways),tourism_context_rows=len(contexts),tourism_selection=len(SELECT),original_section_indicators=len(indicators)),ensure_ascii=False))
if __name__=='__main__':main()
