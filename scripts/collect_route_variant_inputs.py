#!/usr/bin/env python3
"""Freeze primary timetable facts from an explicit local research cache (no network)."""
import csv,datetime as dt,hashlib,json,re,sys
from pathlib import Path
from collect_network_sources import Tables
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'context/17_aircraft_route_review/evidence'
TZ={'AER':3,'ARH':3,'CEK':5,'DME':3,'GOJ':3,'GSV':4,'KJA':7,'KUF':4,'KZN':3,'MMK':3,'MRV':3,'NJC':5,'OMS':6,'PEE':5,'SVX':5,'TJM':5,'UFA':5,'VOG':3,'ZIA':3,'MCX':3,'KGD':2,'REN':5,'BAX':7,'IKT':8,'VVO':10,'KHV':10}
MONTH={'янв':1,'фев':2,'мар':3,'апр':4,'май':5,'мая':5,'июн':6,'июл':7,'авг':8,'сен':9,'окт':10,'ноя':11,'дек':12}
WD={'пн':0,'вт':1,'ср':2,'чт':3,'пт':4,'сб':5,'вс':6}
def write(name,rows):
 with (OUT/name).open('w',encoding='utf-8',newline='')as f:
  w=csv.DictWriter(f,list(dict.fromkeys(k for r in rows for k in r)),lineterminator='\n');w.writeheader();w.writerows(rows)
def main():
 cache=Path(sys.argv[1]if len(sys.argv)>1 else'/tmp/rw_variant_sources');records={};sources=json.load(open(ROOT/'context/12_network_economics/sources.json'));urls={r['id']:r['url']for r in sources}
 for r in csv.DictReader(open(ROOT/'context/12_network_economics/published_flight_dates.csv')):
  if '2026-12-07'<=r['date']<='2026-12-13':
   v={**r,'source_url':urls.get(r['source'],''),'accessed':'2026-11-09','evidence_kind':'REUSED_PRIMARY_PLANNED_SCHEDULE'};records[(r['origin'],r['destination'],r['date'],r['flight'])]=v
 for arrival in [False,True]:
  name='svx_schedule_arr'if arrival else'svx_schedule';file=cache/(name+'.html');html=file.read_text();parser=Tables();parser.feed(html)
  for row in parser.rows:
   if len(row)!=8 or row[-1]not in TZ or not re.match(r'^\d\d:\d\d',row[0]):continue
   dep,arr,days,period,carrier,flight,aircraft,other=row;a,b=(other,'SVX')if arrival else('SVX',other)
   pieces=period.split('/')
   def datepart(x):
    d,mon=re.findall(r'(\d+)\s+([а-я]+)',x.lower())[0];return int(d),MONTH[mon[:3]]
   try:
    dd,mm=datepart(pieces[0]);lo=dt.date(2026 if mm>=10 else 2027,mm,dd);dd,mm=datepart(pieces[-1]);hi=dt.date(lo.year+(mm<lo.month),mm,dd)
   except (IndexError,KeyError,ValueError):continue
   active=range(7)if 'ежеднев' in days.lower()else[WD[x.strip()]for x in days.lower().split(',')if x.strip()in WD]
   clock=lambda x:int(x[:2])*60+int(x[3:5]);duration=clock(arr)+1440*int('(+1)'in arr)-TZ[b]*60-clock(dep)+TZ[a]*60
   while duration<=0:duration+=1440
   for i in range(7):
    d=dt.date(2026,12,7)+dt.timedelta(days=i)
    if lo<=d<=hi and d.weekday()in active:
     v=dict(source=name,origin=a,destination=b,departure_local=dep,arrival_local=arr,weekdays=days,period=period,carrier=carrier,flight=flight,aircraft=aircraft,date=str(d),block_minutes=duration,source_url=urls[name],accessed='2026-11-09',evidence_kind='PRIMARY_PLANNED_SCHEDULE_NOT_ACTUAL_TRACK_OR_PAYLOAD',html_sha256=hashlib.sha256(file.read_bytes()).hexdigest())
     records[(a,b,str(d),flight)]=v
 # Stage16 exact GOJ dates were read separately; do not turn absence of their reverse into a zero.
 for r in csv.DictReader(open(ROOT/'context/16_conditional_decision/research/goj_svx_own_calendar.csv')):
  if (r['origin'],r['destination'],r['date'],r['flight'])not in records:
   records[(r['origin'],r['destination'],r['date'],r['flight'])]={**r,'carrier':'RED WINGS','block_minutes':None,'evidence_kind':'PRIMARY_PLANNED_OWN_FLIGHT_TIME_NOT_FROZEN_IN_STAGE16'}
 rows=[records[k]for k in sorted(records)];write('published_service_facts.csv',rows)
 grouped={}
 for r in rows:
  if r.get('block_minutes')not in [None,'']:
   grouped.setdefault((r['origin'],r['destination']),[]).append(r)
 blocks=[]
 for (a,b),rr in sorted(grouped.items()):
  ssj=[r for r in rr if 'RRJ'in r.get('aircraft','').upper()or'SUPERJET'in r.get('aircraft','').upper()];jets=[r for r in rr if re.search(r'RRJ|SUPERJET|B-|A-',r.get('aircraft','').upper())]
  chosen=ssj or jets
  if not chosen:continue
  blocks.append(dict(origin=a,destination=b,min_published_minutes=min(float(r['block_minutes'])for r in chosen),max_published_minutes=max(float(r['block_minutes'])for r in chosen),aircraft_labels=';'.join(sorted({r['aircraft']for r in chosen})),flights=';'.join(sorted({r['flight']for r in chosen})),source_urls=';'.join(sorted({r['source_url']for r in chosen})),period='2026-12-07/13',status='PLANNED_SSJ_FAMILY_LABEL_NOT_TAIL_MODIFICATION'if ssj else'OTHER_JET_TIMETABLE_PROXY_NOT_SSJ_PERFORMANCE',actual_track_km=None,full_payload_confirmed=None))
 write('directional_blocks.csv',blocks)
 print(json.dumps({'planned_flight_rows':len(rows),'directional_time_rows':len(blocks),'confirmed_tracks':0}))
if __name__=='__main__':main()
