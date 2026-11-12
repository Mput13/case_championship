import csv,datetime,hashlib,io,json,math,urllib.request
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def dump(name,x):(ROOT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def write_csv(name,rows):
 if not rows:raise ValueError(name)
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with (ROOT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def sha(x):return hashlib.sha256(x).hexdigest()
def coord_extract():
 url='https://davidmegginson.github.io/ourairports-data/airports.csv'
 out=ROOT/'inputs/coordinates_selected.json'
 if out.exists():return
 try:raw=urllib.request.urlopen(url,timeout=35).read()
 except Exception as exc:
  dump('sources/COORDINATES_first_fetch_error.json',{'url':url,'error':type(exc).__name__+': '+str(exc),'fallback':'тот же открытый набор автора на GitHub; только GET'})
  url='https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv'
  raw=urllib.request.urlopen(url,timeout=35).read()
 wanted={'VVO','BQS','UUS','PKC','HTA','KHV','IKT','UUD','YKS','SVX','KUF','GOJ','OMS','UFA','KJA','OVB','HRB','PEK','PKX','PVG','CAN','SVO','LED'}
 selected=[]
 for i,r in enumerate(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))),2):
  if r.get('iata_code') in wanted:
   selected.append({'source_row_id':r['id'],'source_row_number':i,'source_row_sha256':sha(json.dumps(r,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()),'iata':r['iata_code'],'lat':float(r['latitude_deg']),'lon':float(r['longitude_deg']),'source_url':url,'source_blob_sha256':sha(raw),'status':'справочные координаты; не AIP и не допуск','unit':'WGS84 degrees','period':'снимок 2026-11-12','coverage':'только перечисленные конечные аэропорты'})
 dump('inputs/coordinates_selected.json',selected)
 dump('sources/COORDINATES.receipt.json',{'source_id':'COORDINATES','url':url,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':sha(raw),'bytes':len(raw),'status':'CAPTURED_FILTERED_ONLY','path':'inputs/coordinates_selected.json','full_dataset_saved':False})
def schedules():
 rows=[];groups={};sums=defaultdict(lambda:{'published_labels':0,'groups':0,'labels':set(),'types':set(),'sources':set()})
 for f in sorted((ROOT/'sources').glob('VVO_API_*.receipt.json')):
  receipt=json.loads(f.read_text());sid=receipt['source_id'];_,_,day,direction=sid.split('_');data=json.loads((ROOT/receipt['path']).read_text())['data']
  for i,r in enumerate(data):
   c={'source_id':sid,'source_url':receipt['url'],'source_blob_sha256':receipt['sha256'],'source_row_id':r['id'],'source_array_index':i,'source_row_sha256':sha(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()),'date_requested':day,'direction':direction,'origin':'VVO' if direction=='1' else r['airport'],'destination':r['airport'] if direction=='1' else 'VVO','flight_label':r['no'],'airline_label':r['airline']['name'],'time_local':r['departure_time'],'clock_semantics':'время у VVO из departure_time API; направление0 требует проверки значения arrival, не использовать как origin departure','aircraft_label':r['aircraft'],'valid_from':r['period_start'],'valid_to':r['period_end'],'weekdays_iso':','.join(r['days_of_week']),'segments_json':json.dumps(r['segments'],ensure_ascii=False),'stops_status':'источник перечисляет остановки' if len(r['segments'])>2 else 'остановки не перечислены; не сертификация nonstop','physical_adjacent_leg_status':'UNKNOWN','unit':'строка опубликованного сезонного предложения','status':'опубликовано; продажа/выполнение/оператор/кресла UNKNOWN','coverage':'аэропорт VVO; только даты выборки; полный рынок не установлен','fare_20kg_rub':'UNKNOWN','booking_lead_days':(datetime.date.fromisoformat(day)-datetime.date(2026,11,12)).days,'inventory_id':'UNKNOWN','nominal_seats':'UNKNOWN','saleable_seats':'UNKNOWN'}
   c.update({'organisation':'АО «Международный аэропорт Владивосток»','as_of':'2026-11-12','retrieved_at':receipt['retrieved_at'],'publication_date':'UNKNOWN','period':day})
   # First source ID component appears shared by marketing labels; this is only a collision group.
   key=(day,direction,r['id'].split('_')[0],r['airport'],r['departure_time'],r['aircraft'])
   c['candidate_physical_group_id']='VVO-G-'+sha('|'.join(key).encode())[:16]
   rows.append(c)
   if key not in groups:groups[key]={'date':day,'direction':direction,'other_airport':r['airport'],'time_local':r['departure_time'],'labels':[],'source_ids':[],'group_id':c['candidate_physical_group_id'],'status':'кандидат одной физической операции; не admission кресел'}
   groups[key]['labels'].append(r['no']);groups[key]['source_ids'].append(sid+':'+r['id'])
 for r in rows:
  week='2026-11-16/22' if r['date_requested'].startswith('2026') else '2027-01-18/24';k=(week,r['direction'],r['origin'],r['destination']);a=sums[k];a['published_labels']+=1;a['labels'].add(r['flight_label'].split('-')[0]);a['types'].add(r['aircraft_label']);a['sources'].add(r['source_id'])
 for key,g in groups.items():
  day,direction,_,other,*_=key;week='2026-11-16/22' if day.startswith('2026') else '2027-01-18/24';k=(week,direction,'VVO' if direction=='1' else other,other if direction=='1' else 'VVO');sums[k]['groups']+=1
 summary=[]
 for (week,direction,a,b),v in sorted(sums.items()):summary.append({'period':week,'origin':a,'destination':b,'published_label_rows':v['published_labels'],'candidate_operation_groups':v['groups'],'carrier_labels':';'.join(sorted(v['labels'])),'aircraft_labels':';'.join(sorted(v['types'])),'source_id':';'.join(sorted(v['sources'])),'unit':'строки/группы за 7 дат; не физические кресла','coverage':'набор аэропортового API, не полный рынок/инвентарь','status':'опубликованное расписание; дедупликация требует подтверждения оператора'})
 write_csv('schedule_observations.csv',rows);dump('schedule_collision_groups.json',list(groups.values()));write_csv('competition_summary.csv',summary)
 return rows,summary
def distance(a,b,coords):
 x,y=coords[a],coords[b];p1,p2=map(math.radians,[x['lat'],y['lat']]);dphi=p2-p1;dl=math.radians(y['lon']-x['lon']);return 6371.0088*2*math.asin(math.sqrt(math.sin(dphi/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2))
def geometry():
 c={x['iata']:x for x in json.loads((ROOT/'inputs/coordinates_selected.json').read_text())}
 pairs=[('VVO',x) for x in ['BQS','UUS','PKC','HTA','KHV','IKT','UUD','YKS','SVX','KJA','OVB','HRB','PEK','PKX','PVG','CAN','SVO','LED']]+[('BQS','UUS'),('HTA','PKC'),('HTA','UUS'),('IKT','PKC'),('SVX','OMS'),('SVX','GOJ'),('SVX','KUF'),('SVX','UFA')]
 rows=[]
 for a,b in pairs:
  km=distance(a,b,c);mid=math.ceil((km/650*60+30)/5)*5
  rows.append({'origin':a,'destination':b,'great_circle_km':round(km,1),'planning_block_min':mid,'lower_planning_min':math.ceil((km/750*60+20)/5)*5,'upper_planning_min':math.ceil((km/600*60+40)/5)*5,'via_VVO_detour_ratio':round((distance(a,'VVO',c)+distance('VVO',b,c))/km,3) if 'VVO' not in [a,b] else 'N/A','unit':'km/minutes/dimensionless','period':'геометрия; сценарный календарь 2027–2028','coverage':'без трассы, ветра, запаса, загрузки, страны пролёта','status':'расчёт геометрии и planning proxy, не flight plan','source_id':'COORDINATES','assumption_id':'VVO-A01;VVO-A02'})
 write_csv('geometry_and_block_proxies.csv',rows);return rows
if __name__=='__main__':
 coord_extract();a,b=schedules();g=geometry();print(json.dumps({'schedule_rows':len(a),'summary_rows':len(b),'geometry_pairs':len(g)},ensure_ascii=False));print(json.dumps([x for x in b if x['origin']=='VVO' and x['destination'] in ['BQS','UUS','PKC','HTA','IKT','KHV','HRB','PKX','PEK']],ensure_ascii=False));print(json.dumps(g[:10],ensure_ascii=False))
