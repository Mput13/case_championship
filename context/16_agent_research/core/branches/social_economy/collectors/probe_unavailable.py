#!/usr/bin/env python3
"""Free, bounded probes; preserves exact TLS failures and skipped-large receipt. No TLS bypass."""
from pathlib import Path
import csv,datetime,json,urllib.parse,urllib.request
ROOT=Path(__file__).resolve().parents[1]
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
rows=[]
for did,u in [('rosstat_primary_population_2025','https://rosstat.gov.ru/storage/mediabank/Сhisl_MO_01-01-2025.xlsx'),('rosstat_primary_income','https://rosstat.gov.ru/storage/mediabank/urov_10subg-nm.xlsx'),('rosstat_primary_grp','https://rosstat.gov.ru/storage/mediabank/VRP_s1998.xlsx')]:
 t=now()
 try:
  with urllib.request.urlopen(urllib.request.Request(urllib.parse.quote(u,safe=':/%'),method='HEAD'),timeout=20) as r:rows.append(dict(dataset_id=did,source_url=u,attempted_at_utc=t,status='LEAD',error='',alternative='HEAD succeeded; GET not run in this probe; inspect collector outputs'))
 except Exception as e:rows.append(dict(dataset_id=did,source_url=u,attempted_at_utc=t,status='ACCESS_FAILED',error=f'{type(e).__name__}: {e}',alternative='Documented Rosstat republication via Tochno; unaffiliated Internet Archive population mirror separately marked. TLS verification remains enabled.'))
u='https://storage.yandexcloud.net/tochno-st-catalog/Rosstat/data_bdmo_118_v20260928/by_indicator/data_section32_112_v20260928.zip';t=now()
try:
 with urllib.request.urlopen(urllib.request.Request(u,method='HEAD'),timeout=20) as r:n=int(r.headers.get('Content-Length','0'))
 rows.append(dict(dataset_id='bdmo_employment_full_section',source_url=u,attempted_at_utc=t,status='LEAD',error=f'NOT_DOWNLOADED size_bytes={n}; exceeds 25 MB per-file cap and needs only selective indicators',alternative='Selected municipal wages Y48213002 acquired; per-indicator and per-year links are in raw/bdmo_indicator_catalog.xlsx'))
except Exception as e:rows.append(dict(dataset_id='bdmo_employment_full_section',source_url=u,attempted_at_utc=t,status='ACCESS_FAILED',error=f'{type(e).__name__}: {e}',alternative='Use indicator catalog and selected indicators'))
with (ROOT/'rejected_or_unavailable.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
(ROOT/'access_probe.json').write_text(json.dumps(dict(probed_at_utc=now(),command='python3 context/16_agent_research/core/branches/social_economy/collectors/probe_unavailable.py',tls_verification=True,results=rows),ensure_ascii=False,indent=2)+'\n')
print({r['dataset_id']:r['status'] for r in rows})
