#!/usr/bin/env python3
"""Точечное расширение первичных месячных релизов KJA. Запускать после build_monthly/finalize_qualification."""
from pathlib import Path
import csv,json,hashlib,re,calendar
P=Path(__file__).resolve().parent;R=P/'sources_receipts'
def read(f):return list(csv.DictReader((P/f).open()))
def write(f,rs):
 with (P/f).open('w',newline='') as o:w=csv.DictWriter(o,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
def rec(k):return json.loads((R/(k+'_receipt.json')).read_text())
def fields(k):
 r=rec(k);return dict(source_ids=k,source_urls=r['url'],source_sha256=r['sha256'],accessed_at_utc=r['accessed_at_utc'])
def text(k):return (R/(k+'.txt')).read_text()
def loc(k,n):
 target=str(n)
 for i,l in enumerate(text(k).splitlines(),1):
  if target in re.sub(r'\s','',l) or (n%1000==0 and str(n//1000)+'тыс' in re.sub(r'[.\s]','',l)):return f'{k}.txt:{i}'
 raise ValueError((k,n))
md=[
 ('KJA_DETAIL_99',1,'2025-02-12',[317243,255697,57427],None),
 ('KJA_DETAIL_100',2,'2025-03-06',[286242,229798,53124],None),
 ('KJA_DETAIL_105',3,'2025-04-08',[326925,264587,59545],[930402,750082,170088]),
 ('KJA_DETAIL_94',4,'2025-05-12',[331744,267227,62209],[1262146,None,None]),
 ('KJA_DETAIL_101',5,'2025-06-11',[338188,None,None],[1600334,None,None]),
 ('KJA_SEARCH_02_D99',6,'2025-07-04',[398105,None,None],[1998439,1609922,366709]),
 ('KJA_DETAIL_102',7,'2025-08-04',[449130,None,None],[2447569,None,None]),
 ('KJA_SEARCH_02_D98',8,'2025-09-05',[455168,None,None],[2903070,None,None]),
 ('KJA_SEARCH_02_D97',9,'2025-10-06',[388347,None,None],[3291416,None,None]),
 ('KJA_SEARCH_02_D104',10,'2025-11-07',[345201,None,None],[3636614,None,None]),
 ('KJA_SEARCH_02_D102',11,'2025-12-04',[310623,237676,69593],[3947237,None,None]),
 ('KJA_DETAIL_98',12,'2026-01-13',[316329,None,69158],[4263566,3459891,803677])]
metric=['всего','внутренние линии','международные линии'];am=[x for x in read('airport_monthly.csv') if x['airport_iata']!='KJA'];ag=read('airport_aggregate_observations.csv');recon=read('reconciliation.csv')
template=read('airport_monthly.csv')[-1]
for k,m,date,vs,yt in md:
 for i,(sc,n) in enumerate(zip(metric,vs)):
  if n is None:continue
  a=dict(template,observation_id=f'KJA-2025{m:02d}-{sc}-MAIN',period_start=f'2025-{m:02d}-01',period_end=f'2025-{m:02d}-{calendar.monthrange(2025,m)[1]:02d}',service_scope=sc,value=n,publication_date=date,source_row_ids=loc(k,n),value_qualifier='REPORTED_INTEGER',aggregation_basis='MONTH',method='DIRECT',organization='Международный аэропорт Красноярск: основной сайт',coverage_status='первичный месячный релиз; межрелизные расхождения сохранены',**fields(k));am.append(a)
 if yt:
  for sc,n in zip(metric,yt):
   if n is None:continue
   b=dict(template,observation_id=f'KJA-2025{m:02d}-{sc}-MAIN-YTD',period_start='2025-01-01',period_end=f'2025-{m:02d}-{calendar.monthrange(2025,m)[1]:02d}',service_scope=sc,value=n,publication_date=date,source_row_ids=loc(k,n),aggregation_basis='YEAR' if m==12 else 'YTD',method='DIRECT',organization='Международный аэропорт Красноярск: основной сайт',coverage_status='отдельная версия основного сайта; не складывать с team.kja.aero',**fields(k));ag.append(b)
 if all(x is not None for x in vs):recon.append(dict(check_id=f'KJA-2025{m:02d}-MAIN-components',scope='месячный total минус ВВЛ минус МВЛ',reported_total=vs[0],computed_comparator=vs[1]+vs[2],difference=vs[0]-vs[1]-vs[2],unit='человек',status='DEFINITION_OR_SOURCE_INCONSISTENCY_UNRESOLVED',source_ids=k,action='Определение прямого транзита не получено; остаток не является оценкой конечных OD'))
for k,date,start,finish,scope,n,kind in [
 ('KJA_SEARCH_2026_D92','2026-07-16','2026-01-01','2026-06-30','международные линии',459000,'YTD'),
 ('KJA_SEARCH_2026_D92','2026-07-16','2025-01-01','2025-06-30','международные линии',372000,'YTD_COMPARATOR_NEW_RELEASE'),
 ('KJA_DETAIL_93','2026-09-22','2026-06-01','2026-08-31','всего',1246736,'SUMMER_BLOCK'),
 ('KJA_DETAIL_93','2026-09-22','2026-06-01','2026-08-31','международные линии',274491,'SUMMER_BLOCK')]:
 b=dict(template,observation_id=f'KJA-{start}-{scope}-{kind}',period_start=start,period_end=finish,service_scope=scope,value=n,value_qualifier='ROUND_PUBLISHED_1000' if k.endswith('D92') else 'REPORTED_INTEGER',publication_date=date,source_row_ids=loc(k,n),aggregation_basis=kind,method='DIRECT',organization='Международный аэропорт Красноярск: основной сайт',coverage_status='период указан прямо; не равномерно распределять по месяцам',**fields(k));ag.append(b)
sum2025=sum(int(x['value']) for x in am if x['airport_iata']=='KJA' and x['service_scope']=='всего')
for cid,total,comp,scope,ids in [
 ('KJA-2025-main-year-components',4263566,3459891+803677,'годовой основной total против ВВЛ+МВЛ','KJA_DETAIL_98'),
 ('KJA-2025-main-monthsum',4263566,sum2025,'сумма 12 опубликованных месячных total против FY',';'.join(x[0] for x in md)),
 ('KJA-2025-international-versions',786939,803677,'две официальные версии международного FY2025','KJA_2025;KJA_DETAIL_98'),
 ('KJA-2025-domestic-versions',3421272,3459891,'две официальные версии внутреннего FY2025','KJA_2025;KJA_DETAIL_98'),
 ('KJA-2025-Jan-revision',317243,317235,'январский релиз против январского comparator в февральском','KJA_DETAIL_99;KJA_DETAIL_100'),
 ('KJA-2025-H1-int-revision',366709,372000,'старый H1 международный против comparator в релизе2026','KJA_SEARCH_02_D99;KJA_SEARCH_2026_D92')]:
 recon.append(dict(check_id=cid,scope=scope,reported_total=total,computed_comparator=comp,difference=comp-total,unit='человек',status='DEFINITION_OR_REVISION_UNRESOLVED',source_ids=ids,action='Сохранить версии раздельно; не смешивать в одном fit без сверки определения'))
write('airport_monthly.csv',am);write('airport_aggregate_observations.csv',ag);write('reconciliation.csv',recon)
# Пары: только опубликованный Top10; его отсутствие вне списка не означает нулевой поток.
segs=read('airport_pair_segment_observations.csv');mapcity={'Москва':'MOW','Сочи':'AER','Новосибирск':'OVB','Санкт-Петербург':'LED','Норильск':'NSK','Иркутск':'IKT','Благовещенск':'BQS','Пхукет':'HKT','Игарка':'IAA','Владивосток':'VVO','Ташкент':'TAS','Екатеринбург':'SVX','Казань':'KZN','Нячанг':'CXR','Камрань':'CXR','Анталья':'AYT','Бангкок':'','Пекин':'','Санья':'SYX'}
# Квартальный Top10 в мартовской публикации сохранён именно как Q1.
for k,m,date,vs,yt in md:
 t=text(k)
 if m==12:
  block=t.split('Самыми популярными направлениями в ушедшем году стали:')[1].split('\n')[0];parts=block.split(',')
 else:
  z=re.search(r'Топ-10 популярных направлений[^:]*:',t)
  if not z:raise ValueError(('missing route table',k))
  block=t[z.end():].split('Топ-10 авиаперевозчиков')[0].split('Традиционные лидеры')[0];parts=[x for x in block.splitlines() if re.search(r'[–]\s*[0-9]',x)][:10]
 parsed=[]
 for l in parts:
  z=re.search(r'^\s*[•]?\s*([^–]+?)\s*[–]\s*([0-9][0-9 ]*)',l)
  if z:parsed.append((z[1].strip(),int(z[2].replace(' ','')),l))
 assert len(parsed)==10,(k,len(parsed),parsed)
 for rank,(name,n,line) in enumerate(parsed,1):
  code=mapcity.get(name,'');sc=segs[0].copy();sc.update(observation_id=f'KJA2025-{m:02d}-TOP{rank:02d}',origin_code='KJA',destination_code=code,destination_kind='CITY_SYSTEM' if code=='MOW' else 'AIRPORT_CODE_MAPPING_CONDITIONAL' if code else 'CITY_AIRPORT_UNKNOWN',period_start='2025-01-01' if m in [3,12] else f'2025-{m:02d}-01',period_end=f'2025-{m:02d}-{calendar.monthrange(2025,m)[1]:02d}',value=n,value_qualifier='REPORTED_INTEGER',direction_basis='UNKNOWN: топ направлений не раскрывает прилёты/вылеты и конечные поездки',source_id=k,source_url=rec(k)['url'],source_sha256=rec(k)['sha256'],publication_date=date,source_row_id=loc(k,n)+f'#top{rank}',assumption_ids='PM-A01;PM-A02;PM-A09;PM-A12');sc['destination_name_original']=name;sc['table_scope']='TOP10_ONLY_NOT_FULL_ROUTE_LIST';segs.append(sc)
# Дополнительные сравнимые летние сегменты LED2025/2026, международные из того же релиза.
for y,name,code,n in [(2025,'Санкт-Петербург','LED',67529),(2026,'Санкт-Петербург','LED',80586),(2025,'Камрань','CXR',20771),(2026,'Камрань','CXR',41978),(2025,'Бангкок','',7230),(2026,'Бангкок','',14859)]:
 sc=segs[-1].copy();k='KJA_DETAIL_93';sc.update(observation_id=f'KJA-{y}-SUMMER-{name}',destination_code=code,destination_kind='AIRPORT_CODE_MAPPING_CONDITIONAL' if code else 'CITY_AIRPORT_UNKNOWN',period_start=f'{y}-06-01',period_end=f'{y}-08-31',value=n,source_id=k,source_url=rec(k)['url'],source_sha256=rec(k)['sha256'],publication_date='2026-09-22',source_row_id=loc(k,n),destination_name_original=name,table_scope='PUBLISHED_SELECTED_SUMMER_COMPARATORS');segs.append(sc)
for x in segs:x.setdefault('destination_name_original','');x.setdefault('table_scope','PUBLISHED_SELECTED_ROUTES')
# CSV schema union is explicit for inherited seven rows.
with (P/'airport_pair_segment_observations.csv').open('w',newline='') as o:
 w=csv.DictWriter(o,fieldnames=list(segs[-1]));w.writeheader();w.writerows(segs)
# Обновление coverage по тем же 20 аэропортам.
cv=read('airport_monthly_coverage.csv')
for x in cv:
 hits=[a for a in am if a['airport_iata']==x['airport_iata'] and a['service_scope']=='всего' and a['period_start'][:7]==x['month']]
 if hits:x.update(status=hits[0]['method'],observation_id=hits[0]['observation_id'],value=hits[0]['value'],meaning_if_missing='',source_ids=hits[0]['source_ids'],next_action='')
write('airport_monthly_coverage.csv',cv)
a=read('assumptions.csv');a.append(dict(assumption_id='PM-A12',assumption='Не смешивать версии статистики KJA; Top10 не полный список',owner_reason='Исследователь P01; два официальных сайта и межрелизные расхождения',range_or_unknown='UNKNOWN: методика total/ВВЛ/МВЛ и величина ревизий; январь317243 против317235',impact_and_how_to_refine='Получить единую форму аэропорта с прямым транзитом; сверить год и все месяцы до fit; непопавшие в Top10 пары не нули',application='Сохранять версии, периоды Q1/FY/месяц и исходные строки; арифметический остаток не endpoint OD'));write('assumptions.csv',a)
s=json.loads((P/'monthly_summary.json').read_text());s.update(airport_monthly_rows=len(am),airport_aggregate_rows=len(ag),primary_pair_segment_rows=len(segs),KJA2025='12 прямых опубликованных месячных total; разрывы версий/арифметики сохранены',KJA2026='H1 международный и летний блок; месяцы не выдуманы');(P/'monthly_summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'airport_monthly_rows':len(am),'segment_rows':len(segs),'KJA2025_monthsum':sum2025,'FY':4263566,'difference':sum2025-4263566},ensure_ascii=False))
