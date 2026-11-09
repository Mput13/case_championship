#!/usr/bin/env python3
"""Stream retained raw ZIPs; independently check municipal grain and regional claims."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import zipfile
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
import review_core_integration as core

BASE = Path(__file__).resolve().parent
OUT = BASE/'reviews'/'core_social_b264780'
PREFIX = 'context/16_agent_research/core/'

def key(r):
    return tuple(r[k]for k in ['region_id','oktmo','mun_level','year'])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--core-raw-root',required=True,type=Path,help='Retained core folder; read only, no raw copied or extracted to disk')
    args=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    m=core.js('social/input_manifest.json')
    core.equal('SOCIAL_MANIFEST_HASH',core.digest(core.get('social/input_manifest.json')),'3837aed1b66efff64242dbf0f5de530f713fbdd197d1a4641caaa9cbe65d7173')
    external=[]
    raw_by_name={}
    for r in m['inputs']:
        if r['source']=='PINNED_GIT_BLOB':
            b=core.get(r['path'],r['git_sha'],False)
            core.equal('SOCIAL_INPUT_HASH',core.digest(b),r['sha256'],r['path'])
        else:
            rel=Path(r['path']).relative_to(PREFIX)
            p=args.core_raw_root/rel
            with p.open('rb')as h:
                hasher=hashlib.sha256()
                for chunk in iter(lambda:h.read(1024*1024),b''):
                    hasher.update(chunk)
            core.equal('SOCIAL_RAW_HASH',hasher.hexdigest(),r['sha256'],r['path'])
            core.equal('SOCIAL_RAW_SIZE',p.stat().st_size,r['size_bytes'],r['path'])
            external.append(dict(path=r['path'],sha256=hasher.hexdigest(),bytes=p.stat().st_size,storage='EXTERNAL_OWNER_RETAINED_READ_ONLY_NOT_COPIED',source_url=r.get('source_url')))
            raw_by_name[p.name]=p
    for r in m['outputs']:
        core.equal('SOCIAL_OUTPUT_HASH',core.digest(core.get('social/'+r['path'])),r['sha256'],r['path'])
    def raw_rows(path):
        with zipfile.ZipFile(path)as z:
            members=[p for p in z.namelist()if p.endswith('.csv')]
            assert len(members)==1
            with io.TextIOWrapper(z.open(members[0]),encoding='utf-8-sig',newline='')as h:
                for no,r in enumerate(csv.DictReader(h,delimiter=';'),2):
                    yield no,r
    groups=[]
    for name in ['tochno_bdmo_municipal_wages.zip','tochno_bdmo_municipal_population.zip']:
        selected=defaultdict(list)
        for no,r in raw_rows(raw_by_name[name]):
            if r['year']=='2024'and r['mun_level']=='Муниципальное образование верхнего уровня':
                selected[key(r)].append((no,r))
        groups.append(selected)
    wages,population=groups
    clean=list(csv.DictReader(io.StringIO(core.get(PREFIX+'branches/social_economy/normalized/example_join_municipal_2024.csv',core.SOURCE,False).decode())))
    clean_by_key={key(r):r for r in clean}
    expected_clean={k for k in wages if len(wages[k])==1 and len(population.get(k,[]))==1 and wages[k][0][1]['mun_type']==population[k][0][1]['mun_type']}
    core.equal('MUNICIPAL_CLEAN_KEYS',set(clean_by_key),expected_clean)
    core.equal('MUNICIPAL_NO_DUPLICATE_KEYS',len(clean_by_key),len(clean))
    comparisons=0
    for k,r in clean_by_key.items():
        wn,w=wages[k][0];pn,p=population[k][0]
        core.equal('WAGE_VALUE',Decimal(r['gross_monthly_wage_rub']),Decimal(w['indicator_value']),str(k))
        core.equal('POPULATION_VALUE',Decimal(r['annual_average_population_persons']),Decimal(p['indicator_value']),str(k))
        core.equal('RAW_ROW_LOCATORS',[int(r['wage_source_row']),int(r['population_source_row'])],[wn,pn],str(k))
        core.equal('UNITS_PERIOD',[w['indicator_unit'],p['indicator_unit'],w['indicator_period']],['Рубль','Человек','Январь-декабрь'],str(k))
        comparisons+=2
    held=set(wages)-expected_clean;population_only=set(population)-set(wages)
    q=core.table('social/municipal_quarantine.csv')
    core.equal('MUNICIPAL_HELD_KEYS',{key(r)for r in q if r['record_class']=='HELD_WAGE_LEFT_JOIN'},held)
    core.equal('POPULATION_ONLY_KEYS',{key(r)for r in q if r['record_class']=='POPULATION_ONLY_COVERAGE'},population_only)
    expected_reasons=Counter()
    for k in held:
        ps=population.get(k,[])
        reason='NO_POPULATION_MATCH'if not ps else ('AMBIGUOUS_KEY'if len(wages[k])!=1 or len(ps)!=1 else'MUNICIPAL_TYPE_MISMATCH_REQUIRES_REVIEW')
        expected_reasons[reason]+=1
    core.equal('MUNICIPAL_HOLD_REASONS',dict(Counter(r['reason']for r in q if r['record_class']=='HELD_WAGE_LEFT_JOIN')),dict(expected_reasons))

    contexts=core.table('social/gateway_region_context_2024.csv')
    wanted={int(r['source_row']):r for r in contexts}
    checked=0
    for no,r in raw_rows(raw_by_name['tochno_regions_tourism.zip']):
        if no not in wanted:
            continue
        c=wanted[no]
        core.equal('TOURISM_RAW_GRAIN',[c['year'],c['region_name'],c['indicator_code'],c['source_edition']],[r['year'],r['object_name'],r['indicator_code'],r['source']],str(no))
        core.equal('TOURISM_LEVEL',r['object_level'],'Регион',str(no))
        core.equal('TOURISM_VALUE',Decimal(c['value']),Decimal(r['indicator_value']),str(no))
        unit=''if r['indicator_unit']=='ND'else r['indicator_unit']
        core.equal('TOURISM_UNIT',c['unit_native'],unit,str(no))
        core.equal('TOURISM_ADMISSION',c['acceptance'],'REGIONAL_ANNUAL_CONTEXT_ONLY'if unit else'QUARANTINE_UNIT_UNKNOWN',str(no))
        checked+=1
    core.equal('TOURISM_ALL_ROWS_CHECKED',checked,len(contexts))
    core.equal('TOURISM_UNIQUE_SOURCE_ROWS',len(wanted),42)
    gateways=core.table('social/gateway_region_crosswalk.csv')
    cities=list(csv.DictReader(io.StringIO(core.get(PREFIX+'normalized/city_version.csv',core.SOURCE,False).decode())))
    census=list(csv.DictReader(io.StringIO(gzip.decompress(core.get(PREFIX+'normalized/large_exports/social_economy__census_2021_settlement_partitions.csv.gz',core.SOURCE,False)).decode())))
    regions=list(csv.DictReader(io.StringIO(core.get(PREFIX+'branches/social_economy/normalized/region_crosswalk.csv',core.SOURCE,False).decode())))
    airports=core.table('inputs/normalized/airport_version.csv')
    for g in gateways:
        a=next(r for r in airports if r['airport_id']==g['airport_id'])
        core.equal('GATEWAY_COORDINATE_HOLD',a['geographic_review'],'',g['airport_iata'])
        if g['airport_iata']=='MRV':
            city=next(r for r in census if r['source_row']==g['source_city_id'].split(':')[-1])
            core.equal('MRV_EXPLICIT_SETTLEMENT',city['settlement_name'],'г. Минеральные Воды')
        else:
            city=next(r for r in cities if r['area_id']==g['source_city_id'])
            core.equal('SOURCE_CITY_LABEL',city['city'],g['city_name'],g['airport_iata'])
        core.equal('SOURCE_REGION_LABEL',city['region'],g['source_region_label'],g['airport_iata'])
        match=[r for r in regions if r['canonical_area_id']==g['canonical_region_id']]
        core.equal('UNIQUE_REGION_CROSSWALK',len(match),1,g['airport_iata'])
        core.equal('REGION_CONTEXT_KEY',match[0]['regional_table_label'],g['regional_table_label'],g['airport_iata'])
        core.equal('NO_RAW_ISO_FALLBACK',g['raw_census_iso_used'],'False',g['airport_iata'])
    result=dict(input_git_sha=core.SHA,frozen_source_sha=core.SOURCE,municipal_clean_keys=len(clean),municipal_numeric_cells_checked=comparisons,wage_source_keys=len(wages),population_source_keys=len(population),held_wage_left_keys=len(held),population_only_keys=len(population_only),hold_reasons=dict(expected_reasons),tourism_raw_rows_checked=checked,regional_context_allowed=sum(r['acceptance']=='REGIONAL_ANNUAL_CONTEXT_ONLY'for r in contexts),tourism_unit_unknown_held=sum(r['acceptance']=='QUARANTINE_UNIT_UNKNOWN'for r in contexts),gateway_source_label_mappings=len(gateways),differences=core.differences,acceptance='PASS_SOURCE_CELLS_AND_EXPLICIT_KEYS_ONLY'if not core.differences else'CHANGES',municipal_boundaries_catchments='NOT_VALIDATED',aggregation='NONE; nested levels not added; population not an earnings weight',forecast='NO_TARGET_LABELS; NOT_ACCEPTED',temporal_limit='Wage/population2024 and regionalannual2024; noDecember2026 seasonality or numeric OD uplift')
    (OUT/'input_manifest.json').write_text(json.dumps(dict(inputs=core.receipts,external_raw=external),indent=2)+'\n')
    (OUT/'reproduction.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n')
    print(json.dumps(result,ensure_ascii=False,default=str));assert not core.differences

if __name__=='__main__':
    main()
