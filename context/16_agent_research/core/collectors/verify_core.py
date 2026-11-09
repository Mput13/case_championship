#!/usr/bin/env python3
"""Small independent evidence checks, including direct ZIP-cell join tracing."""
import csv
import datetime as dt
import gzip
import io
import json
from collections import Counter
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]
def read(f):
    op=gzip.open if f.suffix=='.gz' else open
    with op(f,'rt',encoding='utf-8-sig') as h:return list(csv.DictReader(h))
def main():
    k=read(ROOT/'canonical_keys.csv')
    assert len(k)==len({r['canonical_id'] for r in k})
    ap=read(ROOT/'normalized/airport_version.csv')
    aj=read(ROOT/'normalized/airport_timezone_join.csv')
    assert len(aj)==219 and len({r['airport_id'] for r in aj})==219
    assert sum(r['join_status']=='MATCHED_CODE' for r in aj)==215
    tz=read(ROOT/'normalized/timezone_crosscheck.csv')
    conflicts=[r for r in tz if r['crosscheck_status']=='OFFSET_CONFLICT_REQUIRES_REVIEW']
    byid={r['canonical_id']:r for r in k}
    for r in conflicts:assert byid[r['entity_id']]['iana_timezone']==''
    for r in aj:assert r['iana_timezone']==byid[r['airport_id']]['iana_timezone']
    acc=read(ROOT/'normalized/access_alternative.csv.gz')
    assert len(acc)==96660 and len({(r['origin_area_id'],r['destination_area_id'],r['mode']) for r in acc})==96660
    assert all(r['duration_status']=='MODEL_ESTIMATE' for r in acc if r['distance_hr'])
    assert all(r['missing_reason'] for r in acc if not r['distance_hr'])
    # Join values checked against six original CSV rows, independently of normalized tables.
    social=ROOT/'branches/social_economy'
    joined=read(social/'normalized/example_join_municipal_2024.csv')
    keys=[(r['region_id'],r['oktmo'],r['mun_level'],r['year']) for r in joined]
    assert len(joined)==2022 and len(keys)==len(set(keys))
    assert all(r['year']=='2024' and r['municipal_type_agrees']=='True' for r in joined)
    sample=[joined[0],joined[len(joined)//2],joined[-1]];traces=[]
    for name,rowkey,valuekey in [('municipal_wages','wage_source_row','gross_monthly_wage_rub'),('municipal_population','population_source_row','annual_average_population_persons')]:
        wanted={int(r[rowkey]):r for r in sample}
        with zipfile.ZipFile(social/('raw/tochno_bdmo_'+name+'.zip')) as z:
            member=next(n for n in z.namelist() if n.endswith('.csv'))
            with io.TextIOWrapper(z.open(member),encoding='utf-8-sig') as h:
                for n,raw in enumerate(csv.DictReader(h,delimiter=';'),start=2):
                    if n not in wanted:continue
                    r=wanted[n]
                    assert raw['region_id']==r['region_id'] and raw['oktmo']==r['oktmo'] and raw['year']==r['year']
                    assert float(raw['indicator_value'])==float(r[valuekey])
                    traces.append(dict(archive='tochno_bdmo_'+name+'.zip',member=member,source_row=n,region_id=raw['region_id'],oktmo=raw['oktmo'],year=raw['year'],raw_value=raw['indicator_value'],joined_value=r[valuekey],pass_check=True))
        assert len(traces)%3==0
    assert len(traces)==6
    result=dict(checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),all_pass=True,
        canonical_counts=dict(Counter(r['entity_type'] for r in k)),airport_join=dict(left=219,matched=215,unmatched=4,multiplied_rows=0),
        timezone_conflicts_held=len(conflicts),transport_rows=len(acc),transport_duration_null_rows=sum(not r['distance_hr'] for r in acc),
        municipal_join_rows=len(joined),municipal_join_unique_keys=len(set(keys)),raw_join_cell_traces=traces,
        boundary='Small independent checks; not audit of all source cells, current route execution, airport suitability or economic viability')
    (ROOT/'diagnostics/independent_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key!='raw_join_cell_traces'},ensure_ascii=False))
if __name__=='__main__':main()
