import pathlib,re,html,csv,json,hashlib,datetime
R=pathlib.Path(__file__).parent
clean=lambda x:' '.join(html.unescape(re.sub('<[^>]+>',' ',x)).split())
rows=[]
for sid,direction in [('KHV_SCHEDULE','in'),('KHV_OUT','out')]:
 s=(R/'sources'/f'{sid}.html').read_text();s=re.sub('<!--.*?-->','',s,flags=re.S)
 for i,tr in enumerate(re.findall('<tr[^>]*>(.*?)</tr>',s,re.S),1):
  cells=[clean(v) for v in re.findall('<td[^>]*>(.*?)</td>',tr,re.S)]
  if len(cells)!=7:continue
  city,period,code,flight,days,dep,arr=cells
  code=code or ('S7' if flight.startswith('С7-') else 'UNKNOWN')
  row=dict(row_id=f'{sid}:tr{i}',source_id=sid,source_row_number=i,source_row_sha256=hashlib.sha256(tr.encode()).hexdigest(),direction=direction,city=city,period=period,carrier_marketing_code=code,flight=flight,weekdays=days,departure_local=dep,arrival_local=arr,unit='published_schedule_rule',coverage='one_airport_published_timetable;not_inventory',status='published_not_operated',aircraft_type='UNKNOWN',seats='UNKNOWN',operating_carrier='UNKNOWN',physical_adjacent_leg='UNKNOWN',fare='UNKNOWN',baggage='UNKNOWN',booking_lead_days='UNKNOWN')
  rows.append(row)
with (R/'local_schedule_rows.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
# Expand two deliberately selected source weeks only. Do not annualise.
wd={'ПН':0,'ВТ':1,'СР':2,'ЧТ':3,'ПТ':4,'СБ':5,'ВС':6}
counts={}
for start in ['2026-11-16','2027-01-11']:
 a=datetime.date.fromisoformat(start)
 for row in rows:
  try:lo,hi=[datetime.datetime.strptime(x,'%d.%m.%Y').date() for x in row['period'].split(' - ')]
  except ValueError:continue
  for j in range(7):
   d=a+datetime.timedelta(days=j)
   if lo<=d<=hi and (row['weekdays'].lower()=='ежедневно' or d.weekday() in [wd.get(x,-1) for x in row['weekdays'].split()]):
    key=(start,row['direction'],row['city'],row['carrier_marketing_code']);counts.setdefault(key,[]).append(row['row_id']+':'+str(d))
out=[dict(week_start=k[0],direction=k[1],city=k[2],carrier=k[3],published_rule_instances=len(v),unit='published_station_pair_instances/week',period=k[0]+'/'+str(datetime.date.fromisoformat(k[0])+datetime.timedelta(days=6)),source_id='KHV_SCHEDULE' if k[1]=='in' else 'KHV_OUT',source_row_ids=';'.join(v),coverage='unique_by_rule/date;codeshare_and_physical_overlap_UNRESOLVED',status='diagnostic_not_physical_capacity') for k,v in counts.items()]
with (R/'local_schedule_week_counts.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=out[0].keys());w.writeheader();w.writerows(out)
# Human-readable content without generic privacy-policy footer.
for p in (R/'sources').glob('*.txt'):
 if p.stem in ['KHV_CONTRACT','KHV_MARKETING','LOCAL_SUPPORT']:continue
 t=p.read_text();t=t.split('Политика в отношении обработки персональных данных')[0];p.write_text(t)
print('rules',len(rows),'RW matches',[r['row_id'] for r in rows if r['carrier_marketing_code'] in ['WZ','RW'] or 'РД' in r['flight']]);print('outbound KHV rules')
for r in rows:
 if r['direction']=='out' and r['city'] in ['УЛАН-УДЭ','ЧИТА','БЛАГОВЕЩЕНСК','ЯКУТСК','ПЕТРОПАВЛОВСК-КАМЧАТСКИЙ','ИРКУТСК']:
  print(r['row_id'],r['city'],r['carrier_marketing_code'],r['flight'],r['period'],r['weekdays'],r['departure_local'],r['arrival_local'])
