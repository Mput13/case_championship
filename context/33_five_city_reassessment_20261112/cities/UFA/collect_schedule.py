"""Extract dated published UFA departures; no tickets, browser or credentials.
Run: python3 collect_schedule.py. Needs installed requests and lxml, no install.
_active CSS class is essential: text-only airport pages show all seven weekdays.
Output is published supply, never proof of flown services, occupancy or OD.
"""
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import csv, hashlib, json, re
import requests
from lxml import html
ROOT=Path(__file__).resolve().parent
# Resolve slugs from the official index rather than guessing or treating a 404 as no route.
NAMES={'SVX':'ЕКАТЕРИНБУРГ','MRV':'МИНЕРАЛЬНЫЕ ВОДЫ','GOJ':'НИЖНИЙ НОВГОРОД','SGC':'СУРГУТ','OMS':'ОМСК','TBS':'ТБИЛИСИ','LED':'САНКТ-ПЕТЕРБУРГ','MOW':'МОСКВА','KRR':'КРАСНОДАР','ASF':'АСТРАХАНЬ','TJM':'ТЮМЕНЬ','OVB':'НОВОСИБИРСК','NJC':'НИЖНЕВАРТОВСК','NUX':'НОВЫЙ УРЕНГОЙ','KZN':'КАЗАНЬ','KUF':'САМАРА','NBC':'НИЖНЕКАМСК','PEE':'ПЕРМЬ','TOF':'ТОМСК','KEJ':'КЕМЕРОВО','AER':'СОЧИ','ZIA':'ЖУКОВСКИЙ','NOJ':'НОЯБРЬСК','HMA':'ХАНТЫ-МАНСИЙСК','KVK':'КИРОВСК'}
BASE='https://www.airportufa.ru'
WEEKDAYS=['Пн','Вт','Ср','Чт','Пт','Сб','Вс']
WINDOWS=['2026-11-16','2026-12-07','2027-01-04']
def get(url):
 r=requests.get(url,timeout=35);r.raise_for_status();return r.content
idx=get(BASE+'/schedule/');doc=html.fromstring(idx)
links={' '.join(a.itertext()).strip():a.get('href') for a in doc.xpath('//a[@href]')}
def fetch(item):
 iata,name=item; href=links.get(name)
 if not href:return [],dict(iata=iata,status='not_in_published_index',url=BASE+'/schedule/',limitation='Absence from index is not evidence of no service')
 url=BASE+href if href.startswith('/') else href
 try:
  raw=get(url);tree=html.fromstring(raw);out=[]
  for card in tree.xpath('//div[@class="b-card-sez-card"]'):
   def vals(cl):return [' '.join(x.itertext()).strip() for x in card.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," '+cl+' ")]//*[contains(concat(" ",normalize-space(@class)," ")," b-card-sez-card__info ")]')]
   active=[x.text_content().strip() for x in card.xpath('.//span[contains(@class,"day-week") and contains(concat(" ",normalize-space(@class)," ")," _active ")]')]
   dtext=' '.join(card.xpath('.//*[contains(@class,"__td_period")]//text()'))
   dates=re.findall(r'\d{2}\.\d{2}\.\d{4}',dtext)
   if not dates:raise ValueError('No validity date')
   parsed=[datetime.strptime(x,'%d.%m.%Y').date() for x in dates];start,end=parsed[0],parsed[-1]
   row={'destination':iata,'airline':vals('b-card-sez-card__td_company')[0], 'flight':vals('b-card-sez-card__td_number')[0],'departure':vals('b-card-sez-card__td_time--start')[0],'arrival':vals('b-card-sez-card__td_time--end')[0],'block_time':vals('b-card-sez-card__td_duration')[0],'active_weekdays':'|'.join(active),'valid_from':str(start),'valid_to':str(end),'aircraft':vals('b-card-sez-card__td_flight')[0],'source_url':url}
   out.append(row)
  return out,dict(iata=iata,url=url,status='read',sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),rows=len(out),accessed_at=datetime.now(timezone.utc).isoformat())
 except Exception as exc:return [],dict(iata=iata,url=url,status='error',error=str(exc))
rows=[];logs=[]
with ThreadPoolExecutor(max_workers=5) as pool:
 for rr,ll in pool.map(fetch,NAMES.items()):rows.extend(rr);logs.append(ll)
with (ROOT/'schedule_rows.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary=[]
for window in WINDOWS:
 start=date.fromisoformat(window)
 for iata in NAMES:
  by_airline={};seen={};conflicts=[]
  for row in rows:
   if row['destination']!=iata:continue
   for off in range(7):
    d=start+timedelta(days=off)
    if row['valid_from']<=str(d)<=row['valid_to'] and WEEKDAYS[d.weekday()] in row['active_weekdays'].split('|'):
     key=(str(d),row['flight'])
     # Overlapping validity records of one flight never count twice.
     if key in seen and seen[key]['departure']!=row['departure']:
      conflicts.append({'date':str(d),'flight':row['flight'],'departure_a':seen[key]['departure'],'departure_b':row['departure']})
     seen[key]=row
  for (d,flight),row in seen.items():by_airline[row['airline']]=by_airline.get(row['airline'],0)+1
  summary.append(dict(destination=iata,week_start=window,ambiguous_records=conflicts,published_departures=len(seen) if any(r['destination']==iata for r in rows) else '',by_airline=by_airline,dates_and_flights=[d+' '+fl for d,fl in sorted(seen)]))
(ROOT/'schedule_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
(ROOT/'schedule_fetch_log.json').write_text(json.dumps(logs,ensure_ascii=False,indent=2)+'\n')
for x in summary:print(x['destination'],x['week_start'],x['published_departures'],x['by_airline'])
