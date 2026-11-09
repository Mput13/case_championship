#!/usr/bin/env python3
"""Snapshot the public upstream CSV, preserving all bytes in a compressed raw file."""
from pathlib import Path
from datetime import datetime, timezone
import csv, gzip, hashlib, io, json, urllib.request

ROOT=Path(__file__).resolve().parents[1]
URL="https://davidmegginson.github.io/ourairports-data/airports.csv"

def main():
    req=urllib.request.Request(URL,headers={"User-Agent":"Case5-public-research/1.0"})
    with urllib.request.urlopen(req,timeout=40) as r:
        data=r.read(20_000_001)
        if len(data)>20_000_000:raise ValueError("Source exceeds 20 MB budget")
        status=r.status
    rows=list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    assert rows and 'latitude_deg' in rows[0]
    ru=[r for r in rows if r['iso_country']=='RU']
    packed=gzip.compress(data,mtime=0)
    raw=ROOT/'raw/external/ourairports_global.csv.gz';raw.parent.mkdir(parents=True,exist_ok=True);raw.write_bytes(packed)
    out=ROOT/'normalized/airports_ru.csv'
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(ru)
    meta=dict(dataset_id='HYP-S03',source_url=URL,organisation='OurAirports community / upstream data repository',publication_date='UNKNOWN',retrieved_at_utc=datetime.now(timezone.utc).isoformat(),raw_path=str(raw.relative_to(ROOT)),sha256=hashlib.sha256(packed).hexdigest(),size_bytes=len(packed),compression='gzip',uncompressed_sha256=hashlib.sha256(data).hexdigest(),uncompressed_size_bytes=len(data),record_count=len(rows),geographic_coverage='global; normalized subset iso_country=RU',temporal_coverage='snapshot; per-record validity UNKNOWN',grain='airport',key_fields=['id','ident'],units='coordinates in decimal degrees; elevation in feet',acquisition_status='PARSED',value_type='OBSERVED',http_status=status,license='OurAirports public domain, policy not independently fetched in this run',limitations='Community-maintained coordinates only; not dispatch data; no IANA timezone, market catchment or operating eligibility. The RU classification is a source field, not a legal determination.',collector_version='geometry-collect-v1',command='python3 context/16_agent_research/hypotheses/collectors/collect_geometry.py',transformation='gzip.decompress raw; csv.DictReader; exact iso_country == RU filter',derived_path=str(out.relative_to(ROOT)),derived_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),derived_record_count=len(ru))
    (ROOT/'inputs/geometry_manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'rows_global':len(rows),'rows_ru':len(ru),'raw_compressed_bytes':len(packed),'sha256':meta['sha256']}))

if __name__=='__main__':main()
