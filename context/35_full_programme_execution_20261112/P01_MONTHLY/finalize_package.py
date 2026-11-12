#!/usr/bin/env python3
from pathlib import Path
import csv,json,re,hashlib,datetime
P=Path(__file__).resolve().parent;R=P/'sources_receipts'
def read(f):return list(csv.DictReader((P/f).open()))
def write(f,rs,cols=None):
 with (P/f).open('w',newline='') as o:w=csv.DictWriter(o,fieldnames=cols or list(rs[0]));w.writeheader();w.writerows(rs)
def sf(k):
 r=json.loads((R/(k+'_receipt.json')).read_text());return dict(source_id=k,source_url=r['url'],source_sha256=r['sha256'],accessed_at_utc=r['accessed_at_utc'])
# Национальные контрольные наблюдения. Неполный ряд не интерполируется.
nat=[]
def na(k,start,finish,grain,scope,val,unit,qual,date):
 nat.append(dict(observation_id='NAT'+str(len(nat)+1).zfill(3),period_start=start,period_end=finish,granularity=grain,service_scope=scope,value=val,unit=unit,value_qualifier=qual,organization='Росавиация',publication_date=date,as_of='2026-11-12',calibration_eligibility='контроль только соответствующего национального периода/совокупности; не конечные OD и не 2028 знаменатель',source_row_id=k+'#'+str(len(nat)+1),assumption_ids='PM-A01;PM-A04;PM-A07;PM-A11',**sf(k)))
for sc,v in [('все линии',14800000),('внутренние линии',10900000),('международные линии',3800000)]:na('FAVT_WWW_15135','2025-01-01','2025-02-28','all_russian_carriers_YTD',sc,v,'перевезённые пассажиры, человек','ROUND_PUBLISHED_100000','2025-03-31')
for sc,v in [('все линии',7960000),('внутренние линии',5910000),('международные линии',2050000)]:na('FAVT_WWW_15458','2025-03-01','2025-03-31','all_russian_carriers_MONTH',sc,v,'перевезённые пассажиры, человек','ROUND_PUBLISHED_10000','2025-04-30')
na('FAVT_WWW_15458','2025-01-01','2025-03-31','all_russian_carriers_YTD','все линии',22700000,'перевезённые пассажиры, человек','ROUND_PUBLISHED_100000','2025-04-30')
na('FAVT_16018','2025-01-01','2025-05-31','all_russian_carriers_YTD','все линии',40400000,'перевезённые пассажиры, человек','NEAR_BELOW_UNQUANTIFIED','2025-06-30')
na('FAVT_16018','2025-05-01','2025-05-31','all_russian_carriers_MONTH','все линии',9200000,'перевезённые пассажиры, человек','ROUND_PUBLISHED_100000','2025-06-30')
for sc,v in [('все линии',50800000),('внутренние линии',38100000),('международные линии',12700000)]:na('FAVT_16352','2025-01-01','2025-06-30','all_russian_carriers_YTD',sc,v,'перевезённые пассажиры, человек','ROUND_PUBLISHED_100000','2025-07-31')
for grain,sc,v in [('all_russian_carriers_YTD','все линии',73700000),('all_russian_carriers_YTD','международные линии',17900000),('all_russian_airports_YTD','все линии',144600000),('all_russian_airports_YTD','международные линии',33600000)]:na('FAVT_TG_202508','2025-01-01','2025-08-31',grain,sc,v,'перевезённые пассажиры, человек' if 'carriers' in grain else 'обслуженные пассажиры, человек','ROUND_PUBLISHED_100000','2025-09-30')
for grain,sc,v in [('all_russian_carriers_YEAR','все линии',108850000),('all_russian_carriers_YEAR','внутренние линии',81450000),('all_russian_carriers_YEAR','международные линии',27400000),('all_russian_airports_YEAR','все линии',214660000)]:na('FAVT_17763','2025-01-01','2025-12-31',grain,sc,v,'перевезённые пассажиры, человек' if 'carriers' in grain else 'обслуженные пассажиры, человек','ROUND_PUBLISHED_10000','2026-01-30')
for grain,sc,v in [('all_russian_carriers_YTD','все линии',70550000),('all_russian_carriers_YTD','внутренние линии',52330000),('all_russian_carriers_YTD','международные линии',18220000),('all_russian_airports_YTD','все линии',140300000),('all_russian_airports_YTD','международные линии',35900000)]:na('FAVT_WWW_19665','2026-01-01','2026-08-31',grain,sc,v,'перевезённые пассажиры, человек' if 'carriers' in grain else 'обслуженные пассажиры, человек','ROUND_PUBLISHED_10000' if 'carriers' in grain else 'ROUND_PUBLISHED_100000','2026-10-02')
na('FAVT_WWW_19665','2026-08-01','2026-08-31','all_russian_carriers_MONTH','международные линии',2760000,'перевезённые пассажиры, человек','ROUND_PUBLISHED_10000','2026-10-02')
write('national_aviation_observations.csv',nat)
# В каждой рабочей таблице допустимость калибровки указана прямо.
for fname in ['airport_monthly.csv','airport_aggregate_observations.csv']:
 rs=read(fname)
 for x in rs:x['calibration_status']='HOLD_KJA_DEFINITION_AND_VERSION' if x['airport_iata']=='KJA' else 'CONDITIONAL_AIRPORT_SCALE_ONLY'
 write(fname,rs)
for fname in ['carrier_monthly.csv','carrier_aggregate_observations.csv']:
 rs=read(fname)
 for x in rs:
  helicopter=x['aircraft_mode']=='вертолёты';x['carrier_name']='Группа ЮТэйр: вертолёты' if helicopter else 'Группа ЮТэйр: самолётные перевозки';x['calibration_status']='EXCLUDE_FIXED_WING_MARKET' if helicopter else 'CONDITIONAL_CARRIER_NETWORK_ONLY'
 write(fname,rs)
# Source ledger: в том числе ошибки и discovery-only страницы, без ложного статуса источника.
used={}
def collect(file,idcol,urlcol,hashcol,grain,unitcol='unit'):
 for a in read(file):
  ids=a.get(idcol,'').split(';')
  for sid in ids:
   if not sid:continue
   d=used.setdefault(sid,{'periods':set(),'dates':set(),'units':set(),'grains':set(),'coverage':set()})
   d['periods'].add(a.get('period_start','')+'/'+a.get('period_end',''));d['dates'].add(a.get('publication_date','UNKNOWN'));d['units'].add(a.get(unitcol,''));d['grains'].add(grain);d['coverage'].add(a.get('service_scope',a.get('table_scope','UNKNOWN')))
collect('airport_monthly.csv','source_ids','source_urls','source_sha256','airport_month')
collect('airport_aggregate_observations.csv','source_ids','source_urls','source_sha256','airport_period')
collect('carrier_monthly.csv','source_ids','source_urls','source_sha256','carrier_group_month')
collect('carrier_aggregate_observations.csv','source_ids','source_urls','source_sha256','carrier_group_period')
collect('airport_pair_segment_observations.csv','source_id','source_url','source_sha256','airport_pair_segment_period')
collect('national_aviation_observations.csv','source_id','source_url','source_sha256','national_aviation_period')
for a in read('calibration_eligibility.csv'):
 sid=a['live_evidence_source_id'];d=used.setdefault(sid,{'periods':set(),'dates':set(),'units':set(),'grains':set(),'coverage':set()});d['periods'].add(a['period_start']+'/'+a['period_end']);d['dates'].add(a['publication_date']);d['units'].add(a['unit']);d['grains'].add(a['granularity']);d['coverage'].add('известные потоки: '+a['from_iata'])
source_rows=[]
for file in sorted(R.glob('*_receipt.json')):
 r=json.loads(file.read_text());k=r['source_id'];u=used.get(k);org='Международный аэропорт Владивосток' if k.startswith('VVO') else 'Группа ЮТэйр / инфраструктура Tilda по ссылке официального сайта' if k.startswith('UT') else 'Международный аэропорт Красноярск' if k.startswith('KJA') else 'Росавиация' if k.startswith('FAVT') else 'Росстат' if k.startswith('ROSSTAT') else 'Международный аэропорт Уфа' if k.startswith('UFA') else 'Международный аэропорт Курумоч' if k.startswith('KUF') else 'Аэропорт Кольцово' if k.startswith('SVX') else 'СМИ или зеркало; см. calibration_eligibility'
 org={'KF_SOURCE_01':'СуперОмск / пресс-служба Омского аэропорта','KF_SOURCE_02':'В курсе.ру / Минтранс Пермского края','KF_SOURCE_03':'Коммерсантъ / Аэродинамика','KF_SOURCE_04':'АБН 24 / аэропорт Толмачёво','KF_SOURCE_05':'ИА Амител / Минтранс Алтайского края','KF_SOURCE_06':'Эксперт-Урал / Миндортранс Челябинской области','KF_SOURCE_08':'Samokatus / зеркало пресс-службы группы Аэрофлот'}.get(k,org)
 status='SECONDARY_FETCHED' if k.startswith('KF_SOURCE') else 'PRIMARY_FETCHED' if u else 'DISCOVERY_ONLY'
 if r['status']!='FETCHED':status='ACCESS_ERROR_NOT_DISPROOF'
 if k in ['FAVT_OPEN','FAVT_SZ']:status='DISCOVERY_NO_CURRENT_MONTHLY_TABLE_EXTRACTED'
 source_rows.append(dict(source_id=k,organization=org,url=r['url'],final_url=r.get('final_url',''),accessed_at_utc=r['accessed_at_utc'],publication_date=';'.join(sorted(u['dates'])) if u else 'UNKNOWN',period=';'.join(sorted(u['periods'])) if u else 'UNKNOWN',unit=';'.join(sorted(u['units'])) if u else 'UNKNOWN',granularity=';'.join(sorted(u['grains'])) if u else 'каталог/поиск/описание; наблюдения не извлечены',status=status,coverage=';'.join(sorted(u['coverage'])) if u else 'только поиск источников или проверка доступа',http_status=r.get('http_status',''),error=r.get('error',''),raw_file=r.get('raw_file',''),raw_sha256=r.get('sha256',''),text_file=r.get('text_file',''),text_sha256=hashlib.sha256((R/r['text_file']).read_bytes()).hexdigest() if r.get('text_file') else '',limitation='Доступность URL не доказывает endpoint OD, качество чисел или охват месяцев; точность по строкам'))
write('sources.csv',source_rows)
# Точные ошибки поискового fetch и системного curl сохранены как события, без исправления живых сессий.
events=[{'source':'https://rosstat.gov.ru/statistics/transport','method':'web.open','status':'ACCESS_ERROR','error':'Failed to fetch https://rosstat.gov.ru/statistics/transport: (400) Timeout fetching','consequence':'Публичная недоступность не означает ложность источника; полноценный ряд не заявлен'},{'source':'https://rosstat.gov.ru/statistics/transport','method':'/usr/bin/curl -L --connect-timeout 10 --max-time 35','status':'ACCESS_ERROR','exit_code':60,'error':'curl: (60) SSL certificate problem: self signed certificate in certificate chain','consequence':'TLS-проверка не отключалась; пользовательские браузеры/профили не менялись'}]
(R/'tool_access_events.json').write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n')
# Статус поиска для каждого аэропорта не выдаёт неохваченный поиск за доказанную недоступность.
gaps=[]
for c in read('inputs/city_scope.csv'):
 i=c['iata'];status='SERIES_EXTRACTED' if i=='VVO' else 'FULL_2025_EXTRACTED_2026_PERIOD_BLOCKS' if i=='KJA' else 'ANNUAL_PRIMARY_AND_2026_YTD_ONLY' if i=='UFA' else 'ANNUAL_PRIMARY_ONLY' if i=='KUF' else 'PINNED_REGISTER_ONLY_NO_MONTHLY_EXTRACT'
 gaps.append(dict(airport_iata=i,city=c['city'],investigation_status=status,monthly_2025_rows=sum(1 for a in read('airport_monthly.csv') if a['airport_iata']==i and a['service_scope']=='всего' and a['period_start'].startswith('2025')),monthly_2026_rows=sum(1 for a in read('airport_monthly.csv') if a['airport_iata']==i and a['service_scope']=='всего' and a['period_start'].startswith('2026')),pinned_annual_source_url=c['pax_source_url'],gap_reason='Для оставшихся месяцев/городов текущий ряд не извлечён; это не установление отсутствия публичного источника или рынка',next_action='Помесячная форма аэропорта/Росавиации, определение arrivals/departures/transit; первичные внутренние продажи для endpoint OD'))
write('coverage_gaps.csv',gaps)
s=json.loads((P/'monthly_summary.json').read_text());s.update(VVO2025='11 прямых месячных релизов; декабрь как разность двух округлённых итогов',VVO2026='Прямые январь–сентябрь; январский total опубликован как нижняя граница',UT2025='Январь–сентябрь; январь напрямую, остальные месяцы из соседних YTD; самолёты и вертолёты отдельно',UT2026='Помесячные перевозки не извлечены из доступной официальной ленты; не ноль',national_observations=len(nat),sources_with_receipts=len(source_rows),economic_verdict='Экономика не оценивалась; пакет наблюдений для P05');(P/'monthly_summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'national_rows':len(nat),'sources':len(source_rows),'access_errors':sum(1 for x in source_rows if x['status']=='ACCESS_ERROR_NOT_DISPROOF')},ensure_ascii=False))
