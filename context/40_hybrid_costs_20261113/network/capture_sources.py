#!/usr/bin/env python3
"""Read git objects/P39 raw archive; write minimal, traceable inputs only here."""
import sys
sys.dont_write_bytecode = True
import csv, gzip, hashlib, io, json, re, subprocess
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OWNER = 'f20000e72d5ca934f45f3aaaca4c320750ebccff'
OLD = 'c11eb8c15d32add540d89d086f62487a5b2d424e'
NODES = {'OMS','MOW','IKT','VOG','GOJ','KJA','KUF','BAX','GSV','UUD','AER','MRV'}
MOW = {'SVO','DME','VKO','ZIA'}
CHAINS = {'Прямые MOW-GSV-MRV','Прямые MOW-AER-VOG'}
manifest = []
def sha(b): return hashlib.sha256(b).hexdigest()
def git(rev, path): return subprocess.check_output(['git','show',f'{rev}:{path}'],cwd=ROOT)
def save(relative_path, data, **meta):
    dest = HERE/'source'/relative_path
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(data)
    manifest.append(dict(snapshot_path=str(dest.relative_to(HERE)),sha256=sha(data),bytes=len(data),**meta))
def capture(rev,path,predicate=None):
    original=git(rev,path); data=original
    meta=dict(commit=rev,path=path,source_sha256=sha(original),source_bytes=len(original),selection='FULL')
    if predicate:
        lines=original.decode('utf-8-sig').splitlines(keepends=True)
        rows=list(csv.DictReader(io.StringIO(original.decode('utf-8-sig'))))
        assert len(lines)==len(rows)+1,path
        ix=[i+2 for i,r in enumerate(rows) if predicate(r)]
        data=(lines[0]+''.join(lines[i-1] for i in ix)).encode()
        meta.update(selection='EXACT_HEADER_AND_SELECTED_SOURCE_LINES',source_line_numbers=[1]+ix)
    save(rev[:8]+'/'+path,data,**meta)
def table_bytes(rows):
    f=io.StringIO(newline=''); w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return f.getvalue().encode()

def run():
    p40=HERE.parent
    for name in ['TASK.md','pins.json','inputs/deck_text.json']:
        b=(p40/name).read_bytes();save('p40/'+name,b,path=str((p40/name).relative_to(ROOT)),source_sha256=sha(b),selection='FULL')
    pins=json.loads((p40/'pins.json').read_text())
    deck=(p40/'inputs/team_v7.pptx').read_bytes()
    assert sha(deck)==pins['deck_sha256']
    provenance=dict(pptx_path='context/40_hybrid_costs_20261113/inputs/team_v7.pptx',sha256=sha(deck),bytes=len(deck),
                    pin_match=True,slides_used=[3,4,6,7],usage='TEXT_DATA_ONLY_NO_SLIDE_EDITS',pptx_copied=False)
    save('p40/deck_provenance.json',(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n').encode(),
         path=provenance['pptx_path'],source_sha256=sha(deck),selection='HASH_AND_TEXT_PROVENANCE_NO_BINARY_DUPLICATE')
    for p in ['src/network_model.py','src/demand_model.py','src/rules.py','src/airports_meta.py','src/seasonality.py',
              'docs/37_seasonality.md','data/processed/od_fit.json','data/processed/seasonality_calibration.json',
              'data/processed/aeroflot_domestic_seasonality.csv','data/raw/_manifest.json']:
        capture(OWNER,p)
    for p in ['network','subsidy_hub_airports','siberia_fareast_regions','subsidy_cap_84_103','subsidy_special_fare',
              'resort_airports','demand','range','south_west_regions','bases','longlist_params']:
        capture(OWNER,'data/assumptions/'+p+'.csv')
    for p in ['closed_airports','airport_names','rw_routes_now','favt_airport_names']:
        capture(OWNER,'data/manual/'+p+'.csv')
    capture(OWNER,'data/raw/favt_subsidy_2026.csv')
    capture(OWNER,'data/processed/catchments.csv',lambda r:r['iata'] in (NODES-{'MOW'})|MOW)
    for name in ['od_pairs','demand_estimates','demand_pairs']:
        capture(OWNER,'data/processed/'+name+'.csv',lambda r:r['a'] in NODES and r['b'] in NODES)
    capture(OWNER,'data/processed/airport_seasonality.csv',lambda r:r['iata'] in NODES)
    capture(OWNER,'data/processed/aeroflot_traffic_monthly.csv',lambda r:r['entity']=='group' and r['scope']=='domestic' and
            ((r['metric']=='passengers' and r['month'][:4] in {'2017','2018','2019','2023','2024','2025'}) or
             (r['metric']=='passenger_load_factor' and r['month'][:4] in {'2024','2025'})))
    for rev in [OWNER,OLD]:
        capture(rev,'data/processed/network_routes.csv',lambda r:r['scenario'] in {'base','cautious'} and
                (r['variant']=='Хаб OMS' or r['variant'] in CHAINS))
        capture(rev,'data/processed/network_summary.csv',lambda r:r['scenario'] in {'base','cautious'} and
                (r['hub']=='OMS' or r['variant']=='Прямые рейсы из Москвы и Екатеринбурга'))
    for p in ['src/network_model.py','src/rules.py','data/assumptions/network.csv']:
        capture(OLD,p)
    # P39 code is retained as audit-method provenance; never run its old-network/global export workflow.
    for p in ['audit.py','snapshot_manifest.json','coverage.csv','owner_network_totals.csv']:
        path='context/39_cost_completion_20261113/model_audit/'+p
        b=(ROOT/path).read_bytes();save('p39/'+p,b,path=path,source_sha256=sha(b),selection='FULL')
    fresh=json.loads(git(OWNER,'data/raw/_manifest.json'))
    prior=ROOT/'context/39_cost_completion_20261113/model_audit'
    pm=json.loads((prior/'snapshot_manifest.json').read_text())
    entry=next(x for x in pm if x['path'].endswith('tochno_intercity.csv.gz'))
    packed=(prior/entry['snapshot_path']).read_bytes()
    assert sha(packed)==entry['sha256']
    raw=gzip.decompress(packed)
    assert sha(raw)==fresh['tochno_intercity']['sha256']
    t=pd.read_csv(io.BytesIO(raw),sep=';')
    catch=pd.read_csv(io.BytesIO(git(OWNER,'data/processed/catchments.csv')))
    cities=set(catch[catch.iata.isin((NODES-{'MOW'})|MOW)].main_city)|{'Москва'}
    def wanted(row):
        if row.transport_type=='rail':return row.city_from in cities and row.city_to in cities
        if row.transport_type=='air' and pd.notna(row.distance_km):
            m=re.match(r'\s*([A-Z0-9]{3})\s*—\s*([A-Z0-9]{3})',str(row.comment))
            if m:return all(('MOW' if x in MOW else x) in NODES for x in m.groups())
        return False
    ix=[i for i,r in t.iterrows() if wanted(r)]
    reduced=t.loc[ix].to_csv(index=False,sep=';').encode()
    save(OWNER[:8]+'/data/raw/tochno_selected.csv.gz',gzip.compress(reduced,mtime=0),
         path='data/raw/tochno_intercity/data_intercity_connectivity_162_v20260629.csv',commit=OWNER,
         source_sha256=sha(raw),source_bytes=len(raw),selection='PARSED_SELECTED_ROWS; values preserved; empty/NaN normalized',
         source_row_numbers=[int(i)+2 for i in ix],archive_reuse=str((prior/entry['snapshot_path']).relative_to(ROOT)),
         archive_sha256=sha(packed),owner_manifest_match=True)
    # Capture only actual peer frequencies on the selected physical pairs, no full registry or re-selection.
    routes=list(csv.DictReader(io.StringIO(git(OWNER,'data/processed/network_routes.csv').decode())))
    target_pairs={frozenset((r['from'],r['to'])) for r in routes if r['variant'] in CHAINS}
    peers=[dict(source_line=i+2,**r) for i,r in enumerate(routes) if r['scenario'] in {'base','cautious'} and
           r['variant'].startswith('Прямые ') and frozenset((r['from'],r['to'])) in target_pairs]
    save('direct_pair_allocation_context.csv',table_bytes(peers),commit=OWNER,path='data/processed/network_routes.csv',
         source_sha256=sha(git(OWNER,'data/processed/network_routes.csv')),selection='SELECTED_PHYSICAL_PAIR_CONTEXT_ONLY')
    # Current raw airport-month file is not in owner git. Preserve minimal rows plus 3 annual national sums.
    p=ROOT/'data/raw/favt_airports_2007_2020.csv'; airport_raw=p.read_bytes()
    d=pd.read_csv(io.BytesIO(airport_raw),sep=';',encoding='cp1251').dropna(subset=['Год периода данных'])
    cols=['airport','year']+[f'm{i}' for i in range(1,13)]+['total'];d.columns=cols
    d.year=d.year.astype(int);d=d[d.year.isin([2017,2018,2019])]
    for c in cols[2:14]:d[c]=pd.to_numeric(d[c].astype(str).str.replace(r'\s','',regex=True),errors='coerce')
    names=pd.read_csv(io.BytesIO(git(OWNER,'data/manual/favt_airport_names.csv')))
    target_names={n for r in names[names.iata.isin(NODES)].itertuples() for n in r.favt_names.split(';')}
    sub=d[d.airport.isin(target_names)]
    save('airport_months_selected.csv',sub.to_csv(index=False).encode(),path=str(p.relative_to(ROOT)),
         source_sha256=sha(airport_raw),selection='PARSED_2017_2019_FIXED_AIRPORTS',source_row_numbers=[int(i)+2 for i in sub.index],
         owner_manifest_sha256=fresh['favt_airports']['sha256'],owner_manifest_match=sha(airport_raw)==fresh['favt_airports']['sha256'])
    sums=d.groupby('year')[cols[2:14]].sum().reset_index()
    save('airport_months_national_sums.csv',sums.to_csv(index=False).encode(),path=str(p.relative_to(ROOT)),
         source_sha256=sha(airport_raw),selection='SUM_EACH_MONTH_ALL_ROWS_IN_YEAR; pandas skipna',
         source_row_numbers_by_year={str(y):[int(i)+2 for i in g.index] for y,g in d.groupby('year')})
    diff=subprocess.check_output(['git','diff','--unified=3',OLD,OWNER,'--','src/network_model.py','src/rules.py',
          'src/seasonality.py','docs/37_seasonality.md','data/assumptions/network.csv'],cwd=ROOT)
    save('c11_to_f200_narrow.diff',diff,path='git diff selected computation files',old_commit=OLD,commit=OWNER,selection='EXACT_GIT_DIFF')
    (HERE/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(files=len(manifest),bytes=sum(x['bytes'] for x in manifest),tochno_owner_hash_verified=True,
                         airport_raw_manifest_match=sha(airport_raw)==fresh['favt_airports']['sha256'])))
if __name__=='__main__':run()
