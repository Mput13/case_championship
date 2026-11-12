#!/usr/bin/env python3
"""Собирает квалифицированные наблюдения; никаких оценок OD или экономики."""
from pathlib import Path
import csv,json,hashlib,calendar,datetime,re
P=Path(__file__).resolve().parent;R=P/'sources_receipts'
ASOF='2026-11-12'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,rows,fields=None):
 with (P/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def end(y,m):return f'{y}-{m:02d}-{calendar.monthrange(y,m)[1]:02d}'
def receipt(k):return json.loads((R/(k+'_receipt.json')).read_text())
def sourcefields(ids):
 ids=ids.split(';');rs=[receipt(k) for k in ids]
 return dict(source_ids=';'.join(ids),source_urls=';'.join(x['url'] for x in rs),source_sha256=';'.join(x.get('sha256','') for x in rs),accessed_at_utc=';'.join(x['accessed_at_utc'] for x in rs))
def loc(k,pattern):
 lines=(R/(k+'.txt')).read_text().splitlines()
 for n,l in enumerate(lines,1):
  if pattern in l:return f'{k}.txt:{n}'
 raise ValueError((k,pattern))
# VVO: значения в тысячах опубликованных пассажиров. Точность округления не установлена.
# year,month,source,monthly(total,dom,int),YTD(total,dom,int)
vvo=[
 (2025,1,136,(210,158,52),(210,158,52)),(2025,2,147,(195,148,47),(404,305,99)),
 (2025,3,155,(223,165,58),(627,471,156)),(2025,4,163,(245,187,58),(872,658,214)),
 (2025,5,174,(265,211,54),(1137,869,268)),(2025,6,186,(307,249,58),(1444,1118,326)),
 (2025,7,189,(360,292,68),(1804,1410,394)),(2025,8,196,(379,309,70),(2182,1718,464)),
 (2025,9,203,(334,274,60),(2516,1992,524)),(2025,10,212,(279,212,68),(2796,2204,592)),
 (2025,11,220,(227,165,62),(3023,2369,654)),
 (2026,1,234,(233,164,69),(233,164,69)),(2026,2,239,(214,152,62),(448,316,132)),
 (2026,3,246,(255,178,77),(703,494,209)),(2026,4,257,(279,197,82),(981,690,291)),
 (2026,5,272,(290,213,77),(1272,903,369)),(2026,6,278,(322,243,79),(1594,1146,448)),
 (2026,7,282,(396,301,95),(1990,1447,543)),(2026,8,294,(427,327,100),(2417,1774,643)),
 (2026,9,300,(356,268,88),(2773,2042,731))]
metric=['всего','внутренние линии','международные линии'];months=[];agg=[];reconciliation=[]
vd={}
for f in ['VVO_API_LARGE.html','VVO_API_LARGE_02.html']:
 for x in json.loads((R/f).read_text())['data']:vd[x['id']]=x

def row(k,y,m,scope,value,qual='ROUND_PUBLISHED_1000',method='DIRECT',periodkind='MONTH',organization='АО Международный аэропорт Владивосток',airport='VVO',line=''):
 dat=vd.get(int(k.split('_')[-1]),{}).get('date','') if k.startswith('VVO_ART') else ''
 date='-'.join(dat.split('.')[::-1]) if dat else {'KJA_2025':'2026-01-14','KJA_MONTH_202508':'2025-09-09','UFA_YEAR_2025':'2026-01-27','KUF_YEAR_2025':'2026-01-14','UFA_YTD_202608':'2026-09-29'}.get(k,'UNKNOWN')
 return dict(observation_id=f'{airport}-{y}{m:02d}-{scope}-{periodkind}',airport_iata=airport,metric='обслуженные пассажиры',service_scope=scope,period_start=f'{y}-{m:02d}-01' if periodkind=='MONTH' else f'{y}-01-01',period_end=end(y,m),value=value,unit='человек; события обслуживания в аэропорту',value_qualifier=qual,rounding_rule='UNKNOWN' if qual!='REPORTED_INTEGER' else 'не указано; опубликовано целое число',aggregation_basis=periodkind,direction_basis='UNKNOWN: релиз не задаёт отдельные прилёты/вылеты и правило прямого транзита',carrier_scope='все перевозчики аэропорта по определению издателя',organization=organization,publication_date=date,as_of=ASOF,source_row_ids=line or k,method=method,source_status='PRIMARY_FETCHED',coverage_status='наблюдение только указанной совокупности и периода',allowed_use='масштаб и сезонность этого аэропорта с учётом точности',forbidden_use='endpoint OD; доступный рынок Red Wings; загрузка; выручка; независимое сложение аэропортовых и carrier totals',assumption_ids='PM-A01;PM-A02;PM-A07;PM-A08',**sourcefields(k))
for y,m,sid,vals,ytd in vvo:
 k=f'VVO_ART_{sid}'
 for j,scope in enumerate(metric):
  qual='GT' if y==2026 and m==1 and j==0 else 'ROUND_PUBLISHED_1000'
  # locator: уникальное число плюс логическая метка сохраняют происхождение без новой трактовки.
  pattern=f'{vals[j]} тыс.'
  if pattern not in (R/(k+'.txt')).read_text():pattern='тыс.'
  a=row(k,y,m,scope,vals[j]*1000,qual,line=loc(k,pattern)+f'#month_{j}')
  months.append(a)
  agg.append(row(k,y,m,scope,ytd[j]*1000,qual,periodkind='YTD',line=k+f'#ytd_{j}'))
 # Точный календарь не требует насильно уравнивать округлённые численности.
 reconciliation.append(dict(check_id=f'VVO-{y}{m:02d}-components',scope='месячный всего минус ВВЛ минус МВЛ',reported_total=vals[0]*1000,computed_comparator=(vals[1]+vals[2])*1000,difference=(vals[0]-vals[1]-vals[2])*1000,unit='человек',status='LOWER_BOUND_TOTAL' if y==2026 and m==1 else 'ROUNDING_OR_DEFINITION_UNRESOLVED' if vals[0]!=vals[1]+vals[2] else 'EQUAL_AT_PUBLISHED_PRECISION',source_ids=k,action='Не исправлять исходник; правило округления и ревизии UNKNOWN'))
# FY 2025 отдельно от месяцев; декабрь лишь арифметический proxy из двух округлённых YTD.
for j,scope in enumerate(metric):
 full=[3261,2545,717][j];before=[3023,2369,654][j]
 a=row('VVO_ART_226',2025,12,scope,full*1000,periodkind='YEAR',line='VVO_ART_226#year_'+str(j));agg.append(a)
 a=dict(a,observation_id=f'VVO-202512-{scope}-MONTH',period_start='2025-12-01',aggregation_basis='MONTH',value=(full-before)*1000,method='DIFFERENCE_OF_ROUNDED_ADJACENT_YTD',value_qualifier='DERIVED_FROM_PUBLISHED_1000',source_row_ids=f'VVO_ART_226#year_{j};VVO_ART_220#ytd_{j}',assumption_ids='PM-A01;PM-A02;PM-A07;PM-A08',**sourcefields('VVO_ART_226;VVO_ART_220'))
 months.append(a)
# KJA подтверждённые месяцы: август и декабрь. Domestic декабря не выводим из остатка.
months.append(row('KJA_MONTH_202508',2025,8,'всего',455168,'REPORTED_INTEGER',organization='ООО Аэропорт Емельяново',airport='KJA',line=loc('KJA_MONTH_202508','455 168')))
months.append(row('KJA_2025',2025,12,'всего',316329,'REPORTED_INTEGER',organization='ООО Аэропорт Емельяново',airport='KJA',line=loc('KJA_2025','316 329')))
months.append(row('KJA_2025',2025,12,'международные линии',69158,'REPORTED_INTEGER',organization='ООО Аэропорт Емельяново',airport='KJA',line=loc('KJA_2025','69 158')))
for sc,val in zip(metric,[4263566,3421272,786939]):agg.append(row('KJA_2025',2025,12,sc,val,'REPORTED_INTEGER',periodkind='YEAR',organization='ООО Аэропорт Емельяново',airport='KJA'))
agg.append(row('KJA_MONTH_202508',2025,8,'всего',2903070,'REPORTED_INTEGER',periodkind='YTD',organization='ООО Аэропорт Емельяново',airport='KJA'))
for k,airport,org,y,m,kind,vs,qs in [
 ('UFA_YEAR_2025','UFA','АО Международный аэропорт Уфа',2025,12,'YEAR',[4929715,4000000,900000],['REPORTED_INTEGER','ROUND_PUBLISHED_1000000','ROUND_PUBLISHED_100000']),
 ('KUF_YEAR_2025','KUF','АО Международный аэропорт Курумоч',2025,12,'YEAR',[3570000,2750000,822000],['ROUND_PUBLISHED_10000','ROUND_PUBLISHED_10000','ROUND_PUBLISHED_1000']),
 ('UFA_YTD_202608','UFA','АО Международный аэропорт Уфа',2026,8,'YTD',[3229797,2563649,666148],['REPORTED_INTEGER']*3)]:
 for sc,v,q in zip(metric,vs,qs):agg.append(row(k,y,m,sc,v,q,periodkind=kind,organization=org,airport=airport))
reconciliation.append(dict(check_id='KJA-2025-components',scope='годовой всего минус ВВЛ минус МВЛ',reported_total=4263566,computed_comparator=3421272+786939,difference=4263566-3421272-786939,unit='человек',status='DEFINITION_OR_SOURCE_INCONSISTENCY_UNRESOLVED',source_ids='KJA_2025',action='Не считать остаток трансферными или конечными OD без определения издателя'))
write('airport_monthly.csv',months);write('airport_aggregate_observations.csv',agg)
# Carrier UT: все исходные YTD опубликованы до единицы; monthly является разностью.
ut=[
 (1,'3y60hgb6l1',486827,380144,106683,40788),(2,'0t4ij047p1',932683,725435,207248,74732),
 (3,'falapvjpg1',1419715,1107451,312264,118223),(4,'cbo7zorbd1',1906283,1492264,414019,177589),
 (5,'aejecpi4f1',2417382,1899554,517828,191408),(6,'ddxui4vcs1',2991394,2361065,630329,323398),
 (7,'ga5adlvm41',3608274,2858500,749774,369238),(8,'yhetx524k1',4237222,3365660,871562,438196),
 (9,'8atuo6oia1',4793398,3814397,979001,498337)]
postmeta={}
for f in ['UT_FEED.html','UT_FEED_02.html']:
 for x in json.loads((R/f).read_text())['posts']:postmeta[x['uid']]=x
carrier=[];cagg=[]
for idx,(m,uid,*vals) in enumerate(ut):
 k='UT_POST_'+uid
 for j,scope in enumerate(metric+['вертолёты; всего']):
  mode='вертолёты' if j==3 else 'самолёты';v=vals[j];prior=ut[idx-1][2+j] if idx else 0
  if idx:ids='UT_POST_'+ut[idx-1][1]+';'+k
  else:ids=k
  base=dict(observation_id=f'UT-2025{m:02d}-{scope}',carrier_id='UT_GROUP_FIXED_WING' if mode=='самолёты' else 'UT_GROUP_HELICOPTERS',carrier_name='Группа ЮТэйр: самолётные перевозки' if mode=='самолёты' else 'Группа ЮТэйр: вертолёты',aircraft_mode=mode,metric='перевезённые пассажиры',service_scope=scope,period_start=f'2025-{m:02d}-01',period_end=end(2025,m),value=v-prior,unit='человек; перевезённые пассажиры по определению компании',value_qualifier='DIFFERENCE_REPORTED_INTEGERS' if idx else 'REPORTED_INTEGER',organization='Группа ЮТэйр; первичная пресс-служба',publication_date=postmeta[uid]['date'][:10],as_of=ASOF,source_row_ids=(f'{k}#ytd_{j}' if not idx else f'UT_POST_{ut[idx-1][1]}#ytd_{j};{k}#ytd_{j}'),method='DIFFERENCE_OF_ADJACENT_YTD' if idx else 'DIRECT',source_status='PRIMARY_FETCHED',coverage_status='январь–сентябрь 2025; состав самолётной совокупности требует подтверждения однородности',allowed_use='контроль соответствующей carrier совокупности и условной сезонности; fixed-wing отдельно от helicopter',forbidden_use='endpoint OD; сезонность любой новой RW пары; сумма группы и её части; вертолёты в авиарынок самолётов',assumption_ids='PM-A04;PM-A07;PM-A08',**sourcefields(ids))
  carrier.append(base)
  cagg.append(dict(base,observation_id=base['observation_id']+'-YTD',period_start='2025-01-01',value=v,value_qualifier='REPORTED_INTEGER',method='DIRECT_YTD',source_row_ids=f'{k}#ytd_{j}',**sourcefields(k)))
 # Наблюдённый контроль ВВЛ+МВЛ = самолёты в каждом первичном отчёте.
 reconciliation.append(dict(check_id=f'UT-2025{m:02d}-components',scope='YTD самолёты минус ВВЛ минус МВЛ',reported_total=vals[0],computed_comparator=vals[1]+vals[2],difference=vals[0]-vals[1]-vals[2],unit='человек',status='EQUAL_AT_PUBLISHED_PRECISION' if vals[0]==vals[1]+vals[2] else 'INCONSISTENT',source_ids=k,action='Самолётная совокупность; вертолёты отдельно'))
# Годовое сравнение UT — округлённый итог, не дополнительные месяцы.
for j,(scope,val,qual) in enumerate([('всего',6200000,'ROUND_PUBLISHED_100000'),('внутренние линии',5000000,'ROUND_PUBLISHED_1000000'),('вертолёты; всего',700000,'ROUND_PUBLISHED_100000')]):
 b=carrier[0].copy();k='UT_POST_r4azhkuii1';b.update(observation_id=f'UT-2025-YEAR-{j}',aircraft_mode='вертолёты' if j==2 else 'самолёты',carrier_id='UT_GROUP_HELICOPTERS' if j==2 else 'UT_GROUP_FIXED_WING',service_scope=scope,period_start='2025-01-01',period_end='2025-12-31',value=val,value_qualifier=qual,publication_date='2026-04-30',source_row_ids=k+'#year_'+str(j),method='DIRECT_YEAR',coverage_status='годовой округлённый итог; октябрь–декабрь по месяцам UNKNOWN',**sourcefields(k));cagg.append(b)
write('carrier_monthly.csv',carrier);write('carrier_aggregate_observations.csv',cagg)
# Сверки published monthly vs YTD: никаких исправлений исходников.
for y in [2025,2026]:
 for j,scope in enumerate(metric):
  relevant=[x for x in months if x['airport_iata']=='VVO' and x['period_start'].startswith(str(y)) and x['service_scope']==scope]
  total=sum(x['value'] for x in relevant);last=[x for x in agg if x['airport_iata']=='VVO' and x['period_end']==('2025-12-31' if y==2025 else '2026-09-30') and x['service_scope']==scope][0]
  reconciliation.append(dict(check_id=f'VVO-{y}-{j}-monthsum',scope='сумма доступных месячных значений минус соответствующий YTD/FY',reported_total=last['value'],computed_comparator=total,difference=total-last['value'],unit='человек',status='LOWER_BOUND_IN_SUM' if y==2026 and j==0 else 'ROUNDING_OR_REVISION_UNRESOLVED' if total!=last['value'] else 'EQUAL_AT_PUBLISHED_PRECISION',source_ids=';'.join(x['source_ids'] for x in relevant),action='Не балансировать искусственно; числа из разных релизов округлены, допуск издателя UNKNOWN'))
write('reconciliation.csv',reconciliation)
# Заявленная совокупность 20 городов; отсутствие ряда = gap, не ноль.
coverage=[]
for c in csv.DictReader((P/'inputs/city_scope.csv').open()):
 for y,nmonths in [(2025,12),(2026,10)]:
  for m in range(1,nmonths+1):
   hit=[x for x in months if x['airport_iata']==c['iata'] and x['period_start']==f'{y}-{m:02d}-01' and x['service_scope']=='всего']
   coverage.append(dict(airport_iata=c['iata'],city=c['city'],month=f'{y}-{m:02d}',status=hit[0]['method'] if hit else 'GAP_NOT_OBSERVED',observation_id=hit[0]['observation_id'] if hit else '',value=hit[0]['value'] if hit else '',unit='обслуженные пассажиры, человек',meaning_if_missing='в этой исследовательской выгрузке ряд не установлен; не отсутствие перевозок' if not hit else '',source_ids=hit[0]['source_ids'] if hit else '',next_action='Получить месячный отчёт аэропорта или актуальную форму Росавиации; не распределять годовой total вручную' if not hit else ''))
write('airport_monthly_coverage.csv',coverage)
# Не навязываем сезонные веса. Наблюдённый ряд VVO подходит для проверки proxy, а не переноса на все пары.
(P/'monthly_summary.json').write_text(json.dumps({'as_of':ASOF,'airport_monthly_rows':len(months),'airport_aggregate_rows':len(agg),'carrier_monthly_rows':len(carrier),'carrier_aggregate_rows':len(cagg),'airport_scope_count':20,'coverage_grid_months':22,'coverage_grid_rows':len(coverage),'VVO2025':'11 direct month reports; December derived from rounded FY minus Nov YTD','VVO2026':'Jan-Sep direct month reports; Jan total lower bound','UT2025':'Jan-Sep; direct Jan and differences of adjacent reported YTD; fixed wing separate from helicopter','UT2026':'GAP: no monthly traffic release found in available official feed (not zero)','endpoint_od_confirmed_rows':0,'economic_verdict':'NOT_EVALUATED; это пакет наблюдений для P05'},ensure_ascii=False,indent=2)+'\n')
print((P/'monthly_summary.json').read_text())
