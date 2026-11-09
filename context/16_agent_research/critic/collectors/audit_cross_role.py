#!/usr/bin/env python3
"""Freeze narrow in-progress inputs and independently check keys/geometry/metadata.

Default replay is offline from our snapshots. --capture explicitly refreshes them;
no colleague code is imported or executed. Raw acquisition bytes remain in core.
"""
import argparse
import collections
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import zipfile

BASE = Path(__file__).resolve().parents[1]
WORKTREES = Path('/Users/a/.t3/worktrees/case_championship')
CORE = WORKTREES / 'research-case5-raw-core-20261109/context/16_agent_research/core'
HYP = WORKTREES / 'research-case5-hypotheses-20261109/context/16_agent_research/hypotheses'
SNAP = BASE / 'evidence' / 'cross_role_snapshot_v2'

def sha(b): return hashlib.sha256(b).hexdigest()
def read(p): return list(csv.DictReader(p.open(encoding='utf-8-sig', newline='')))
def capture():
    inputs = []
    selections = {
        'core': (CORE, ['progress.md', 'acquisition_manifest.json', 'diagnostics/normalization_checks.json', 'diagnostics/timezone_checks.json', 'normalized/airport_version.csv', 'normalized/airport_timezone_join.csv', 'normalized/canonical_keys.csv', 'normalized/city_version.csv', 'normalized/city_airport_candidate_links.csv', 'collectors/check_timezones.py']),
        'hypotheses': (HYP, ['progress.md', 'candidates.csv', 'experiments_queue.csv', 'normalized/city_scope.csv', 'normalized/geometry_legs.csv', 'normalized/geometry_paths.csv', 'normalized/reproduced_thresholds.csv', 'normalized/screen_summary.json', 'collectors/screen_candidates.py'])}
    for role, (root, paths) in selections.items():
        for name in paths:
            src = root / name
            if not src.exists(): continue
            b = src.read_bytes(); dest = SNAP / role / name
            dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(b)
            inputs.append(dict(role=role, path=str(dest.relative_to(BASE)), source_path=str(src), bytes=len(b), sha256=sha(b)))
    out = dict(captured_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(), source_status='IN_PROGRESS; files may change concurrently; not final submission', inputs=inputs)
    (SNAP / 'manifest.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')

def unique(rows, fields):
    keys = [tuple(r[f] for f in fields) for r in rows]
    return dict(rows=len(rows), distinct=len(set(keys)), duplicate_rows=len(keys)-len(set(keys)))

def distance(a,b):
    la,lo,lb,lob=map(math.radians,[float(a['latitude_deg']),float(a['longitude_deg']),float(b['latitude_deg']),float(b['longitude_deg'])])
    h=math.sin((lb-la)/2)**2+math.cos(la)*math.cos(lb)*math.sin((lob-lo)/2)**2
    return 2*6371.0088*math.asin(min(1,math.sqrt(h)))

def main():
    p=argparse.ArgumentParser();p.add_argument('--capture', action='store_true');args=p.parse_args()
    if args.capture: capture()
    manifest=json.loads((SNAP/'manifest.json').read_text())
    assert all(sha((BASE/e['path']).read_bytes())==e['sha256'] for e in manifest['inputs'])
    c=SNAP/'core';h=SNAP/'hypotheses'
    raw_checks=[]
    for e in json.loads((c/'acquisition_manifest.json').read_text())['datasets']:
        if e['acquisition_status'] != 'ACQUIRED_RAW': continue
        q=CORE/e['raw_path'];stored=q.read_bytes();b=gzip.decompress(stored) if e.get('compression')=='gzip' else stored
        assert sha(b)==e['sha256'],e['dataset_id']
        if e.get('compressed_sha256'): assert sha(stored)==e['compressed_sha256']
        count=None;special={}
        if e['dataset_id']=='tochno_intercity_zip':
            with zipfile.ZipFile(io.BytesIO(b)) as z:
                members=[n for n in z.namelist() if n.endswith('.csv') and not n.startswith('__MACOSX/')]
                assert len(members)==1,members
                member=members[0]
                rows=list(csv.DictReader(io.StringIO(z.read(member).decode('utf-8-sig')),delimiter=';'))
            keys={(r['oktmo_from'],r['oktmo_to'],r['transport_type']):r for r in rows}
            special=dict(pair_mode_unique=len(keys)==len(rows),rows=len(rows),member=member,reverse_mismatch_count=sum(any(r[f]!=keys[(r['oktmo_to'],r['oktmo_from'],r['transport_type'])][f] for f in ['distance_km','distance_hr','source']) for r in rows),scope='Reverse-direction copies are not independent observations; provider-estimated durations are not train schedules')
            count=len(rows)
        elif e['suffix']=='csv': count=sum(1 for _ in csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
        elif e['suffix']=='json': count=len(json.loads(b))
        if count is not None and e.get('record_count') is not None: assert count==e['record_count'],e['dataset_id']
        raw_checks.append(dict(dataset_id=e['dataset_id'],external_path=str(q),sha256=sha(b),stored_sha256=sha(stored),record_count=count,bytes_validated=True,semantic_truth_validated=False,**special))
    airports=read(c/'normalized/airport_version.csv');joins=read(c/'normalized/airport_timezone_join.csv');cities=read(c/'normalized/city_version.csv');links=read(c/'normalized/city_airport_candidate_links.csv')
    ap={r['airport_id']:r for r in airports};ci={r['area_id']:r for r in cities}
    mismatch=[dict(airport_id=r['airport_id'],iata=r['iata_code'],usable_main_timezone=ap[r['airport_id']]['iana_timezone'],auxiliary_timezone=r['iana_timezone'],main_validation=ap[r['airport_id']].get('timezone_validation_status')) for r in joins if r['iana_timezone']!=ap[r['airport_id']]['iana_timezone']]
    d=json.loads((c/'diagnostics/normalization_checks.json').read_text());stale=[]
    for e in d['normalized_files']:
        q=c/e['path']
        if q.exists() and sha(q.read_bytes()) != e['stored_sha256']: stale.append(dict(path=e['path'],expected=e['stored_sha256'],actual=sha(q.read_bytes())))
    candidates=read(h/'candidates.csv');legs=read(h/'normalized/geometry_legs.csv');paths=read(h/'normalized/geometry_paths.csv');scope=read(h/'normalized/city_scope.csv');queue=read(h/'experiments_queue.csv');airport={r['airport_iata']:r for r in scope}
    geometry_errors=[]
    for r in legs:
        got=float(r['distance_km']);calculated=distance(airport[r['origin']],airport[r['destination']])
        if abs(got-calculated)>0.00051:geometry_errors.append(dict(candidate_id=r['candidate_id'],path_id=r['path_id'],leg=r['leg_index'],exported=got,recomputed=calculated))
    for r in paths:
        ll=[v for v in legs if (v['candidate_id'],v['path_id'])==(r['candidate_id'],r['path_id'])]
        if abs(sum(float(v['distance_km']) for v in ll)-float(r['total_chord_km']))>0.003:geometry_errors.append(dict(candidate_id=r['candidate_id'],path_id=r['path_id'],error='path_sum'))
    out=dict(generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(), snapshot_manifest=str((SNAP/'manifest.json').relative_to(BASE)), scope=manifest['source_status'],
        core=dict(raw_checks=raw_checks,keys={'airport':unique(airports,['airport_id']),'city':unique(cities,['area_id']),'timezone_aux':unique(joins,['airport_id']),'candidate_link':unique(links,['area_id','airport_id'])},timezone_cross_table_mismatches=mismatch,stale_normalization_hashes=stale,airport_join_rows=len(joins),airport_iata_rows=sum(bool(r['iata_code']) for r in airports),links_foreign_keys_valid=all(r['area_id'] in ci and r['airport_id'] in ap for r in links),candidate_link_scope='Geographic chord <=75km; no travel-time/catchment or demand inference',timezone_scope='Published assertion plus nearby-city conflict diagnostic; not legal timezone assignment or airport-boundary verification'),
        hypotheses=dict(candidate_keys=unique(candidates,['candidate_id']),candidates=len(candidates),queue_rows=len(queue),geometry_paths=len(paths),geometry_legs=len(legs),airport_scope=len(scope),geometry_errors=geometry_errors,economic_status_counts=dict(collections.Counter(r['evaluation_status'] for r in candidates)),demand_status_counts=dict(collections.Counter(r['demand_status'] for r in candidates)),numeric_demand_count=sum(bool(r['demand_value']) for r in candidates),numeric_fare_count=sum(bool(r['net_fare_rub']) for r in candidates),interpretation='Geometry independently reproduced, not route approval or profitability; research priority is not expected-profit ranking'),
        acceptance=('HOLD conflicting timezone auxiliary until consistent; ' if mismatch else 'Timezone auxiliary now agrees with usable main fields; ')+('publish a current final normalized hash manifest or label the old normalization diagnostic as historical; ' if stale else '')+'hypotheses geometry accepted only as DERIVED research lead; no market/fleet/operational acceptance')
    (BASE/'evidence'/'cross_role_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(core_timezone_mismatches=len(mismatch),stale_core_hashes=len(stale),core_keys=out['core']['keys'],hypotheses=out['hypotheses']),ensure_ascii=False))

if __name__=='__main__':main()
