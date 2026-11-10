#!/usr/bin/env python3
"""Expand captured published rules for one named week, retaining duplicate/conflict lineage."""
import csv,datetime,re,pathlib,json,collections
R=pathlib.Path(__file__).resolve().parent
START=datetime.date(2026,12,7);END=datetime.date(2026,12,13)
MON={'янв':1,'фев':2,'мар':3,'апр':4,'мая':5,'июн':6,'июл':7,'авг':8,'сен':9,'окт':10,'ноя':11,'дек':12}
DAYS={'пн':0,'вт':1,'ср':2,'чт':3,'пт':4,'сб':5,'вс':6}
def read(n):return list(csv.DictReader(open(R/n)))
def write(n,rows):
 keys=list(dict.fromkeys(k for x in rows for k in x))
 with (R/n).open('w',newline='') as f:w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)
def parse_dates(x):
 p=x['period'];ds=[]
 for d,m,y in re.findall(r'(\d{2})\.(\d{2})\.(\d{4}|\d{2})',p):
  ds.append(datetime.date(int(y) if len(y)==4 else 2000+int(y),int(m),int(d)))
 if ds:return ds
 for d,m in re.findall(r'(\d{1,2})\s+(янв|фев|мар|апр|мая|июн|июл|авг|сен|окт|ноя|дек)',p.lower()):
  month=MON[m];ds.append(datetime.date(2026 if month>=4 else 2027,month,int(d)))
 return ds
expanded=[];held=[]
for x in read('service_observations.csv'):
 if x['date']:
  dates=[datetime.date.fromisoformat(x['date'])];basis='inherited_dated_instance'
 else:
  ds=parse_dates(x)
  if not ds or len(ds)>2:held.append(dict(observation_id=x['observation_id'],reason='PERIOD_UNPARSED',period=x['period']));continue
  a=ds[0];b=ds[-1];text=x['weekdays'].lower()
  weekdays=set(range(7)) if 'ежедневно' in text else {v for k,v in DAYS.items() if k in text}
  if not weekdays:
   held.append(dict(observation_id=x['observation_id'],reason='WEEKDAYS_UNPARSED',period=x['period']));continue
  dates=[START+datetime.timedelta(days=i) for i in range(7) if a<=START+datetime.timedelta(days=i)<=b and (START+datetime.timedelta(days=i)).weekday() in weekdays]
  basis='full_year_rule' if re.search(r'\.\d{4}|\.\d{2}',x['period']) else 'winter_2026_2027_year_assigned'
 for d in dates:
  if not START<=d<=END:continue
  expanded.append(dict(route=x['route'],origin=x['origin'],destination=x['destination'],date=d.isoformat(),flight=x['flight'].replace(' ',''),carrier=x['carrier'],departure_local=x['departure_local'],arrival_local=x['arrival_local'],aircraft=x['aircraft'],source_id=x['source_id'],source_url=x['source_url'],observation_id=x['observation_id'],locator=x['locator'],date_basis=basis,raw_sha256=x['raw_sha256'],status='PUBLISHED_NOT_EXECUTED; NO_RESIDUAL_SEATS_OR_FINAL_FARE'))
write('dated_service_records.csv',expanded)
# A flight published by two airports remains one departure. Conflicting clocks/types stay variants.
group=collections.defaultdict(list)
for x in expanded:group[(x['origin'],x['destination'],x['date'],x['flight'])].append(x)
instances=[]
for k,items in sorted(group.items()):
 a,b,d,flight=k
 variants=sorted({(x['departure_local'],x['arrival_local'],x['aircraft']) for x in items})
 instances.append(dict(route=items[0]['route'],origin=a,destination=b,date=d,flight=flight,carriers=';'.join(sorted({x['carrier'] for x in items})),departure_local=' | '.join(sorted({x['departure_local'] for x in items})),arrival_local=' | '.join(sorted({x['arrival_local'] for x in items})),aircraft=' | '.join(sorted({x['aircraft'] for x in items})),publication_records=len(items),source_ids=';'.join(sorted({x['source_id'] for x in items})),observation_ids=';'.join(x['observation_id'] for x in items),clock_or_type_conflict=len(variants)>1,oneway_departures=1,unit='unique published origin-destination-date-flight; incomplete market',period_start=START,period_end=END,observation_vs_model='PUBLISHED_DATE_INSTANCE_YEAR_AS_NOTED',capacity_remaining='UNKNOWN',price_final='UNKNOWN',operating_nonstop_status='PUBLISHED_ROUTE; stop status not independently guaranteed'))
write('dated_service_instances.csv',instances)
summary=[]
for k,items in __import__('itertools').groupby(sorted(instances,key=lambda x:(x['route'],x['origin'],x['destination'],x['carriers'])),lambda x:(x['route'],x['origin'],x['destination'],x['carriers'])):
 items=list(items);summary.append(dict(route=k[0],origin=k[1],destination=k[2],carriers=k[3],oneway_departures=len(items),dates=';'.join(sorted({x['date'] for x in items})),flights=';'.join(sorted({x['flight'] for x in items})),aircraft=';'.join(sorted({x['aircraft'] for x in items})),period_start=START,period_end=END,unit='published departures in one direction in this7-day window; no annual extension',complete_market=False,capacity_or_fare='UNKNOWN'))
write('weekly_service_context.csv',summary)
checks=dict(expanded_records=len(expanded),unique_instances=len(instances),duplicates_collapsed=len(expanded)-len(instances),conflicting_instances=sum(x['clock_or_type_conflict'] for x in instances),held=held,status='OFFLINE_EXPANSION_ONLY')
(R/'dated_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n');print(json.dumps(checks,ensure_ascii=False))
