#!/usr/bin/env python3
"""Bounded additional public downloads. Exact bytes, safe headers, no auth.

Groups also preserve reproducible URLs of initial inline acquisitions. --group geo
or favt repeats those public GETs to a NEW timestamped directory; historical inputs
remain untouched. For exact normalization replay, use retained historical snapshots.
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
SAFE={'content-type','content-length','last-modified','etag','date','cache-control'}
GROUPS={
 'market':[
  ('svx_2025_route_traffic','https://ar-svx.ru/about/news/razvitie-infrastruktury-novye-servisy-i-rost-passazhiropotok/','html','Аэропорт Кольцово','airport route segment aggregate','Published route-specific passenger movements, not final OD or new airline share','UNKNOWN'),
  ('svx_january_2025_route_traffic','https://ar-svx.ru/about/news/v-yanvare-passazhiry-koltsovo-chashche-vsego-letali-otdykhat/','html','Аэропорт Кольцово','airport route segment aggregate','Historical month for seasonal scale crosscheck; not December forecast','UNKNOWN'),
 ],
 'carrier':[
  ('travelpayouts_airlines','https://api.travelpayouts.com/data/ru/airlines.json','json','Travelpayouts','airline code directory','IATA airline codes and names; does not prove currently operating carrier','UNKNOWN'),
  ('openflights_airlines','https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat','csv','OpenFlights','airline code directory','Historical community directory with active flags of unknown freshness; crosswalk only','Open Database License; verify repository terms'),
  ('ourairports_github_readme','https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/README.md','txt','OurAirports','documentation','License and distribution provenance','Public domain per repository'),
  ('openflights_license','https://raw.githubusercontent.com/jpatokal/openflights/master/LICENSE','txt','OpenFlights','documentation','Reuse terms for directory','UNKNOWN until read'),
 ],
 'geo':[
  ('geonames_cities15000','https://download.geonames.org/export/dump/cities15000.zip','zip','GeoNames','populated place','Independent city and timezone crosscheck, no population common reference year','CC BY 4.0'),
  ('iana_zone1970','https://raw.githubusercontent.com/eggert/tz/main/zone1970.tab','tab','IANA tz maintainers','timezone','Timezone ID and Russia region reference','Public domain except stated exceptions'),
  ('iana_zone','https://raw.githubusercontent.com/eggert/tz/main/zone.tab','tab','IANA tz maintainers','timezone','Timezone ID reference','Public domain except stated exceptions'),
  ('iana_europe','https://raw.githubusercontent.com/eggert/tz/main/europe','txt','IANA tz maintainers','timezone history','Timezone transitions and primary legal reference links','Public domain except stated exceptions'),
  ('geonames_readme','https://download.geonames.org/export/dump/readme.txt','txt','GeoNames','documentation','Fields and reuse license','CC BY 4.0'),
 ],
 'favt':[
  ('favt_2025_market','https://www.favt.gov.ru/novosti-novosti/?id=17763&version=print','html','Росавиация','market aggregates','National denominator not OD','UNKNOWN'),
  ('favt_airport_open_data','https://favt.gov.ru/opendata/7714549744-statperevaeroportpas/','html','Росавиация','data catalog','Airport historical monthly series; verify period','UNKNOWN'),
  ('favt_carrier_statistics','https://www.favt.gov.ru/dejatelnost-vozdushnye-perevozki-osnovnye-proizvodstvennye-pokazateli-ga/','html','Росавиация','statistics page','Carrier metrics with source definition','UNKNOWN'),
 ],
 'mintrans':[
  ('mintrans_2025_transport_report','https://www.mintrans.gov.ru/file/562566','pdf','Минтранс РФ','national indicators','2025 denominator and airport service counts, same administrative lineage','UNKNOWN'),
 ]
}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--group',required=True,choices=GROUPS);args=ap.parse_args()
 stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');dest=ROOT/'raw/additional'/stamp;dest.mkdir(parents=True,exist_ok=True);entries=[]
 for id,url,suffix,org,grain,use,license in GROUPS[args.group]:
  e=dict(dataset_id=id,source_url=url,organization=org,grain=grain,decision_use=use,license=license,retrieved_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),publication_date='UNKNOWN',geographic_coverage='World; Russia crosswalk where applicable',temporal_coverage='Mutable snapshot',key_fields='Per source',units='Per source',limitations=use,collector_version='acquire-additional-v1',command='python3 context/16_agent_research/core/collectors/acquire_additional.py --group '+args.group)
  try:
   with urllib.request.urlopen(url,timeout=45) as r:body=r.read(15_000_001);e['http_status']=r.status;e['response_headers']={k:v for k,v in r.headers.items() if k.lower() in SAFE}
   if len(body)>15_000_000:raise ValueError('15MB per file cap')
   f=dest/(id+'.'+suffix);f.write_bytes(body);e.update(raw_path=str(f.relative_to(ROOT)),sha256=hashlib.sha256(body).hexdigest(),size_bytes=len(body),compression='none',acquisition_status='ACQUIRED_RAW',record_count=None)
   if suffix=='json':e['record_count']=len(json.loads(body))
   elif suffix=='csv':e['record_count']=len(list(csv.reader(io.StringIO(body.decode('utf-8-sig')))))
  except Exception as x:e.update(acquisition_status='ACCESS_FAILED',raw_path=None,sha256=None,record_count=None,error=type(x).__name__+': '+str(x))
  entries.append(e);print(id,e['acquisition_status'],e.get('size_bytes'),e.get('record_count'),e.get('error',''),flush=True)
 (ROOT/('additional_'+args.group+'_'+stamp+'_manifest.json')).write_text(json.dumps(dict(datasets=entries),ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
