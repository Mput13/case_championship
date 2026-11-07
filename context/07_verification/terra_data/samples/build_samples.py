#!/usr/bin/env python3
"""Без зависимостей; повторная загрузка изменит snapshot. Вывод только рядом со скриптом."""
import csv, hashlib, io, json, datetime, urllib.request
from html.parser import HTMLParser
from pathlib import Path
P=Path(__file__).resolve().parent
HEADERS={'User-Agent':'Mozilla/5.0'}
A='https://davidmegginson.github.io/ourairports-data/airports.csv'
S='https://favt.gov.ru/dejatelnost-vozdushnye-perevozki-subsidirovanie-regiony/'
R='https://flyredwings.com/en/press/news/red-wings-so-2-avgusta-nachnet-perevozit-passazhirov-izhavia-iz-ekaterinburga-v-izhevsk/'
def get(u):
 with urllib.request.urlopen(urllib.request.Request(u,headers=HEADERS),timeout=45) as f: return f.read()
def digest(x):return hashlib.sha256(x).hexdigest()
def write(name, fields, rows):
 with (P/name).open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n'); w.writeheader();w.writerows(rows)
a=get(A); s=get(S); r=get(R)
reader=csv.DictReader(io.StringIO(a.decode('utf-8-sig')))
codes={'SVX','IJK','KZN','OVB','KJA','UFA','PEE','KUF'}
rows=[x for x in reader if x['iata_code'] in codes and x['iso_country']=='RU']
assert len(rows)==8, [(x['iata_code'],x['name']) for x in rows]
fields=['id','ident','type','name','latitude_deg','longitude_deg','elevation_ft','iso_country','iso_region','municipality','scheduled_service','icao_code','iata_code']
write('ourairports_ru.csv',fields,[{k:x[k] for k in fields} for x in rows])
class Rows(HTMLParser):
 def __init__(self): super().__init__(); self.rows=[]; self.row=None;self.cell=None
 def handle_starttag(self,t,a):
  if t=='tr': self.row=[]
  elif t in ('td','th') and self.row is not None:self.cell=[]
 def handle_data(self,d):
  if self.cell is not None:self.cell.append(d)
 def handle_endtag(self,t):
  if t in ('td','th') and self.cell is not None:
   self.row.append(' '.join(''.join(self.cell).replace('\xa0',' ').split()));self.cell=None
  elif t=='tr' and self.row is not None:self.rows.append(self.row);self.row=None
p=Rows();p.feed(s.decode('utf-8'))
sub=[x for x in p.rows if len(x)==11 and x[0].isdigit() and x[7].find('2026')>=0][:8]
assert len(sub)==8 and sub[0][2:4]==['Абакан','Чита'],sub
fields=['source_row','airline','origin_name','destination_name','distance_km_oneway','aircraft_type_text','seats_as_published','period_text','flights_per_week_as_published','round_trips_2026_as_published','note']
write('favt_regional_subsidy_2026.csv',fields,[dict(zip(fields,x)) for x in sub])
text=r.decode('utf-8')
for x in ['17:40','18:45','20:00','21:05','2026']:
 assert x in text,x
rows=[]
for date in [datetime.date(2026,8,d) for d in (2,7,9,14)]:
 for origin,dest,time in [('SVX','IJK','20:00' if date.weekday()==6 else '17:40'),('IJK','SVX','21:05' if date.weekday()==6 else '18:45')]:
  rows.append(dict(date=date.isoformat(),origin=origin,destination=dest,carrier='Red Wings',departure_local=time,aircraft='SSJ-100',status='announced_schedule',flight_number='',transformation='calendar expansion of 1 Aug press release'))
write('redwings_announced_aug2026.csv',list(rows[0]),rows)
manifest={'retrieved_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_snapshots':[{'url':u,'sha256':digest(b),'size_bytes':len(b),'retained':'no; source content read in memory'} for u,b in [(A,a),(S,s),(R,r)]], 'files':[]}
for n,detail in [('ourairports_ru.csv','8 исходных записей RU, выбор по IATA; первичные данные сообщества, не авиационная эксплуатационная документация'),('favt_regional_subsidy_2026.csv','первые восемь полных строк таблицы с 11 ячейками; строки с rowspan пропущены; сохраняются оригинальные значения'),('redwings_announced_aug2026.csv','8 строк: календарное раскрытие опубликованного плана, 2/7/9/14 августа в двух направлениях; не факт выполнения'),('build_samples.py','процедура выгрузки и формирования CSV')]:
 b=(P/n).read_bytes();manifest['files'].append({'path':n,'sha256':digest(b),'bytes':len(b),'description':detail})
(P/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
