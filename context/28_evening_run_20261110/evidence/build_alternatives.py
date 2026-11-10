#!/usr/bin/env python3
"""Source-qualified direct/connecting alternatives and concrete timing examples."""
import csv,pathlib,re,datetime,json,collections,itertools
from zoneinfo import ZoneInfo
R=pathlib.Path(__file__).resolve().parent

def read(n):return list(csv.DictReader(open(R/n)))
def write(n,rows):
 fields=list(dict.fromkeys(k for x in rows for k in x))
 with (R/n).open('w',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
pubs=read('dated_service_instances.csv');subs=read('subsidy_route_matches.csv');zones={x['iata_code']:x['iana_timezone'] for x in read('raw/git/4a9971be/context/21_visual_explainer_draft_20261110/inputs/airports.csv') if x['iana_timezone']}
paths=[('C01','NJC>SVX>MRV','existing northern carrier plus southern carrier'),('C01','UFA>SVX>MRV','alternative to UFA-MRV direct'),('C03','KUF>SVX>OMS','RW or Utair feed plus RW OMS'),('C03','KUF>NJC','listed Azimut direct competitor'),('C03','KUF>MRV','listed Azimut direct competitor'),('C04','OMS>SVX>UFA','existing carrier legs; no new OMS base assumed'),('C04','OMS>KJA','Rossiya published direct, Aeroflot listed program carrier'),('C07','SVX>KJA','existing direct competitor to SVX-OMS-KJA through journey'),('C10','UFA>SGC','Utair published direct, intermittent charters retained'),('C10','UFA>SVX>SGC','alternative via SVX'),('C14','KVX>MRV','Azimut program list and July regulator repost; winter timing unresolved'),('C17','PEE>RGK','UVT direct published through27Dec2026'),('C17','PEE>SVX>MMK','comparison candidate; PEE-SVX published leg not captured'),('C31','SVX>MRV','Aeroflot/Ural published direct competition'),('C33','GOJ>SVX>OMS','same published RW network with retiming alternatives'),('C35','IJK>SVX>OMS','operator of IJK-SVX must be resolved before partnership claim')]
rows=[];examples=[]
def route(a,b):return '-'.join(sorted((a,b)))
def utc_options(x,arrival=False):
 zone=ZoneInfo(zones[x['destination'] if arrival else x['origin']]);d=datetime.date.fromisoformat(x['date']);out=[]
 for text in x['arrival_local' if arrival else 'departure_local'].split('|'):
  m=re.search(r'(\d{2}):(\d{2})',text)
  if not m:continue
  delta=1 if '+1' in text else 0
  t=datetime.datetime.combine(d+datetime.timedelta(days=delta),datetime.time(int(m[1]),int(m[2])),tzinfo=zone).astimezone(datetime.timezone.utc);out.append(t)
 return out
for cid,path,desc in paths:
 pts=path.split('>');leg_evidence=[]
 for a,b in zip(pts,pts[1:]):
  ps=[x for x in pubs if x['origin']==a and x['destination']==b];ss=[x for x in subs if x['route']==route(a,b)]
  leg_evidence.append(dict(a=a,b=b,published_departures=len(ps),program_rows=len(ss)))
 row=dict(hypothesis=cid,network=cid+'_alternative_context',path=path,route=route(pts[0],pts[-1]),comparison=desc,period='2026-12-07/13 for dated instances; program list2026 separate',legs=json.dumps(leg_evidence,ensure_ascii=False),status='PUBLISHED_LEGS_ONLY' if all(x['published_departures'] for x in leg_evidence) else ('PARTIAL_PROGRAM_OR_LEG_EVIDENCE' if any(x['published_departures'] or x['program_rows'] for x in leg_evidence) else 'GAP_NOT_ABSENCE'),through_ticket='UNKNOWN',protected_connection='UNKNOWN',MCT='UNKNOWN_NOT_ASSUMED',residual_seats='UNKNOWN',total_final_fare_20kg='UNKNOWN',rail_or_ground='Dated comparator NOT_DONE; absence not inferred',observation_vs_model='OBSERVED_PUBLICATIONS_WITH_AUTHORED_PATH_COMPARISON')
 rows.append(row)
 if len(pts)!=3:continue
 aa=[x for x in pubs if x['origin']==pts[0] and x['destination']==pts[1]];bb=[x for x in pubs if x['origin']==pts[1] and x['destination']==pts[2]]
 candidates=[]
 for x,y in itertools.product(aa,bb):
  if x['origin'] not in zones or x['destination'] not in zones or y['destination'] not in zones:continue
  xd=utc_options(x);xa=utc_options(x,True);yd=utc_options(y);ya=utc_options(y,True)
  # Remove only an inferred local midnight wrap when source omitted +1.
  xa=[v+datetime.timedelta(days=1) if v<=min(xd) else v for v in xa]
  ya=[v+datetime.timedelta(days=1) if v<=min(yd) else v for v in ya]
  waits=[(v-u).total_seconds()/60 for u,v in itertools.product(xa,yd)]
  if not waits or min(waits)<=0 or max(waits)>1440:continue
  elapsed=[(v-u).total_seconds()/60 for u,v in itertools.product(xd,ya)]
  candidates.append(dict(hypothesis=cid,path=path,leg1_date=x['date'],leg1_flight=x['flight'],leg1_departure_local=x['departure_local'],leg1_arrival_local=x['arrival_local'],leg2_date=y['date'],leg2_flight=y['flight'],leg2_departure_local=y['departure_local'],leg2_arrival_local=y['arrival_local'],connection_min_minutes=min(waits),connection_max_minutes=max(waits),elapsed_min_minutes=min(elapsed),elapsed_max_minutes=max(elapsed),leg1_source_ids=x['source_ids'],leg2_source_ids=y['source_ids'],leg1_observation_ids=x['observation_ids'],leg2_observation_ids=y['observation_ids'],source_clock_or_type_conflict=x['clock_or_type_conflict']=='True' or y['clock_or_type_conflict']=='True',timezone_input='pinned context21airports IANA',filter='chronology positive and <=24h only; not MCT, bookability or capacity acceptance',classification='DERIVED_TIMING_EXAMPLE_FROM_PUBLISHED_LEGS'))
 if candidates:examples.append(min(candidates,key=lambda x:(x['elapsed_max_minutes'],x['leg1_date'])))
write('alternative_paths.csv',rows);write('alternative_timing_examples.csv',examples)
print('paths',len(rows),'concrete timing examples',len(examples))
