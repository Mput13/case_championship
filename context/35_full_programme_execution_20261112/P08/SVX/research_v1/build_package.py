"""Воспроизводимый Stage A SVX; git show только exact SHA; никакой денежной модели."""
import calendar
import csv
import datetime as dt
import hashlib
import io
import json
import math
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]
PREFIX='context/35_full_programme_execution_20261112/'
PINS={
 'BASE':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6',
 'FIVE':'c18f7640ea36647a05b39089e5293f22dd009f63',
 'PLAN':'b7d74e67dd6c603db049b1915b1afec987e3b458',
 'P00R':'b7d74e67dd6c603db049b1915b1afec987e3b458',
 'P02':'d9486f113f074c185a94bcc5c0afeef12ea3574f',
 'P03':'79dc698b99dfe866886d32376ed388e85bdd039c',
 'P04':'620a0ac4bb11763319c4227485f6a3996b91d367',
 'P06':'982f13d9b6c378ed9581125ecc5c40f17dade6a3',
}
INPUTS=[]; CACHE={}; SOURCE_ROWS=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def jd(o):return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def writej(name,obj):
 (ROOT/name).parent.mkdir(parents=True,exist_ok=True)
 (ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def writec(name,rows,fields=None):
 (ROOT/name).parent.mkdir(parents=True,exist_ok=True)
 if fields is None:fields=list(dict.fromkeys(k for r in rows for k in r))
 with (ROOT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fields);w.writeheader()
  for r in rows:w.writerow({k:(jd(v) if isinstance(v,(list,dict)) else ('UNKNOWN' if v is None else v)) for k,v in r.items()})
def read(key,path):
 ck=(key,path)
 if ck not in CACHE:
  raw=subprocess.check_output(['git','show',PINS[key]+':'+path],cwd=REPO)
  INPUTS.append({'source_id':key+':'+path,'commit':PINS[key],'git_path':path,'sha256':sha(raw),'bytes':len(raw),'access':'git show exact SHA','coverage':'закреплённая версия; актуальность будущего периода не предполагается'})
  CACHE[ck]=raw.decode()
 return CACHE[ck]
def table(key,path):return list(csv.DictReader(io.StringIO(read(key,path))))
def extract(key,path,predicate,name):
 rs=table(key,path);out=[]
 for i,r in enumerate(rs):
  if predicate(r):
   provenance={'pinned_commit':PINS[key],'pinned_git_path':path,'source_csv_record_number':i+1,'pinned_row_locator':f'csv_data_record:{i+1}',
       'source_row_sha256':sha(jd(r).encode()),'row_hash_method':'sha256 canonical JSON original DictReader row; source headers/order preserved separately by file hash'}
   out.append({**r,**provenance})
   SOURCE_ROWS.append({'extract_file':name,**provenance,'source_row_id':next((r[k] for k in ['product_id','schedule_instance_id','market_id','card_id','rate_id','budget_component_id','source_id'] if r.get(k)),str(i+1))})
 writec(name,out,fields=list(out[0]) if out else ['source_locator','source_row_sha256'])
 return out

EPS=['OMS','KUF','UFA','GOJ','KJA','MRV','SGC','KZN','VOG','RGK','MMK']
CONTROLS=[('SVX','KVX'),('KVX','MRV'),('SVX','PEE'),('PEE','MRV'),('PEE','MMK'),('PEE','RGK'),('OMS','KJA'),('KUF','VOG'),('UFA','SGC'),('UFA','NUX'),('KUF','NUX'),('KUF','MRV'),('BAX','HTA'),('IKT','UUD'),('UUD','HTA'),('SCW','ARH'),('ARH','MMK'),('IJK','SVX'),('KRO','SVX'),('MQF','SVX')]
PAIRSET={frozenset(('SVX',e)) for e in EPS}|{frozenset(x) for x in CONTROLS}
def relevant(r):
 a=r.get('origin',r.get('from_iata',r.get('a','')));b=r.get('destination',r.get('to_iata',r.get('b','')))
 return frozenset((a,b)) in PAIRSET

def primary_schedule_rows():
 """Строки SVX table: clocks, weekdays, validity, carrier, flight, type, airport."""
 out=[]
 city_names={'Омск':'OMS','Самара':'KUF','Уфа':'UFA','Нижний Новгород':'GOJ','Красноярск':'KJA','Минеральные Воды':'MRV','Сургут':'SGC','Казань':'KZN','Волгоград':'VOG','Горно-Алтайск':'RGK','Мурманск':'MMK'}
 for sid in ['SVX_DEP','SVX_ARR']:
  raw=(ROOT/'evidence'/f'{sid}_full_text.txt').read_text(); lines=raw.splitlines()
  plain=[x.split(': ',1)[1] for x in lines]
  for i,v in enumerate(plain):
   if not re.fullmatch(r'[A-Z0-9]{2}-[0-9]+',v) or i<5 or i+2>=len(plain):continue
   ep=plain[i+2]
   if ep not in EPS:continue
   segment=plain[i-5:i+3]
   if not re.fullmatch(r'\d\d:\d\d(?: \(\+1\))?',segment[0]):continue
   if not re.fullmatch(r'\d\d:\d\d(?: \(\+1\))?',segment[1]):continue
   row={'source_id':sid,'source_text_locator':f'text_lines:{i-4}-{i+3}',
     'origin':'SVX' if sid=='SVX_DEP' else ep,'destination':ep if sid=='SVX_DEP' else 'SVX',
     'departure_local':segment[0],'arrival_local':segment[1],'weekdays_ru':segment[2],
     'validity_source_text':segment[3],'carrier_source_label':segment[4],'flight':v,'aircraft_source_label':segment[6],
     'year_assignment':'2026/27 inferred seasonal context; acceptance pending P02','unit':'опубликованное правило расписания, локальные часы',
     'status':'published_not_inventory_not_legal_operator_proof','coverage':'одна первичная таблица; полный рынок UNKNOWN',
     'url':'https://ar-svx.ru/schedule/'+('?type=arr' if sid=='SVX_ARR' else ''),
     'source_text_sha256':sha(raw.encode()),'assumption_id':'P08-SVX-A17'}
   row['record_id']='SVX-PRIMARY-'+sha(jd(row).encode())[:16]
   row['row_sha256']=sha(jd(row).encode());out.append(row)
 writec('evidence/SVX_primary_schedule_products.csv',out)
 return out

def main():
 (ROOT/'evidence').mkdir(exist_ok=True)
 primary=primary_schedule_rows()
 p02=extract('P02',PREFIX+'P02/competitor_products.csv',relevant,'evidence/P02_products_selected.csv')
 coverage=extract('P02',PREFIX+'P02/market_coverage.csv',relevant,'evidence/P02_market_coverage_selected.csv')
 fares=extract('P02',PREFIX+'P02/fare_panel.csv',lambda r:any(r.get('market_id') in [f'AIR:SVX:{e}',f'AIR:{e}:SVX'] for e in EPS),'evidence/P02_fares_selected.csv')
 hist=extract('P02',PREFIX+'P02/historical_demand_context.csv',relevant,'evidence/P02_historical_demand_selected.csv')
 extract('P02',PREFIX+'P02/calendar_inventory.csv',lambda r:relevant(r) and ('2026-12-07'<=r.get('departure_date','')<='2026-12-13' or '2027-01-04'<=r.get('departure_date','')<='2027-01-10'),'evidence/P02_dated_offer_windows.csv')
 extract('P02',PREFIX+'P02/clock_conflicts.csv',lambda r:'SVX' in str(r),'evidence/P02_clock_conflicts_SVX.csv')
 baseline=extract('BASE','data/manual/rw_routes_now.csv',relevant,'evidence/BASE_rw_routes_selected.csv')
 cards=extract('BASE','data/external/colleagues/route_product_cards.csv',relevant,'evidence/BASE_cards_selected.csv')
 blockrefs=extract('BASE','context/12_network_economics/block_times.csv',relevant,'evidence/BASE_block_selected.csv')
 # Воспроизводимая геометрия только для исторических цепочек, без спроса/тарифа.
 coords=table('BASE','data/processed/destinations.csv');coord={r['to']:(float(r['lat']),float(r['lon'])) for r in coords}
 coord['RGK']=((51+57/60+35.38/3600+51+58/60+42.69/3600)/2,(85+49/60+45.60/3600+85+50/60+37.13/3600)/2)
 selected_coords=[{'iata':e,'lat':coord[e][0],'lon':coord[e][1],'source':'BASE:data/processed/destinations.csv','status':'геометрический вход закреплённой модели'} for e in sorted(set(sum([list(x) for x in CONTROLS],[])+EPS)) if e in coord]
 writec('evidence/airport_coordinates_selected.csv',selected_coords)
 for r in selected_coords:
  if r['iata']=='RGK':r.update(source='RGK_TECH: midpoint of published runway thresholds02/20',status='сценарная точка геометрии; не навигационная ARP')
 writec('evidence/airport_coordinates_selected.csv',selected_coords)
 read('BASE','data/assumptions/network.csv');read('BASE','data/assumptions/bases.csv')
 read('FIVE','context/33_five_city_reassessment_20261112/cities/PEE/dossier.md')
 read('FIVE','context/33_five_city_reassessment_20261112/cities/GOJ/dossier.md')
 read('P03',PREFIX+'P03/aircraft_type_parameters.csv')
 read('P03',PREFIX+'P03/sp_adapter/ordinary_return_lower_bound.json')
 read('P03',PREFIX+'P03/sp_adapter/prior_task_refs.csv')
 read('P03',PREFIX+'P03/sp_adapter/crew_advisory.json')
 read('P00R',PREFIX+'P00R/contract_addendum.json')
 contract=json.loads(read('P06',PREFIX+'P06/producer_contract.json'))
 read('P06',PREFIX+'P06/README.md')
 plan=json.loads(read('PLAN','context/34_full_programme_plan_20261112/variant_research_plan.json'))
 rates=table('P04',PREFIX+'P04/event_rate_map.csv')
 budgets=table('P04',PREFIX+'P04/budget_components.csv')
 read('P04',PREFIX+'P04/financial_cost_coverage.csv')
 extract('P03',PREFIX+'P03/existing_commitments.csv',lambda r:'SVX' in str(r) or any(x in str(r) for x in ['WZ1081','WZ5303']),'evidence/P03_commitments_selected.csv')

 # Минуты направленные. Это выбранные проектные аналоги, не dispatch-планы SJ100/ПД8.
 BM={'OMS':(100,105),'KUF':(105,105),'UFA':(75,75),'GOJ':(120,115),'KJA':(185,200),'MRV':(215,200),'SGC':(105,110),'KZN':(100,95),'VOG':(160,145),'RGK':(160,175),'MMK':(200,185)}
 OFF={'SVX':5,'OMS':6,'KUF':4,'UFA':5,'GOJ':3,'KJA':7,'MRV':3,'SGC':5,'KZN':3,'VOG':3,'RGK':7,'MMK':3,'PEE':5,'KVX':3,'NUX':5,'NJC':5}
 # Доходы и реальные когорты не задаются этим пакетом.
 A=[]
 def ass(i,value,unit,basis,range_,effect,sensitivity,refine):
  A.append({'assumption_id':'P08-SVX-A'+i,'value':value,'unit':unit,'selected_by':'P08-SVX-A, исследователь Sol6.1 xhigh','basis':basis,
    'range_or_unknown':range_,'approval_status':'выбор исследователя для условного сравнения; не решение команды','affected_conclusions':effect,'sensitivity':sensitivity,'refinement':refine})
 ass('01',BM,'мин/плечо','P02 направленные длительности; BASE block_times; новые первичные расписания SVX 12.11.2026. SGC 105/110, RGK160/175, MMK200/185 из локальных часов с UTC. Для SJ100/ПД8 только аналог.',
     'сценарный стресс 0.9x/1.0x/1.2x; статистические границы UNKNOWN','время оборота, ресурс, расходы; типы не взаимозаменяемы','пересчитать все цепочки при 1.2x; маршрут/нагрузка могут выйти за сценарий','P03: тип, хвост, трасса, сезон, payload, блок-время и допуски')
 ass('02',45,'мин/turn','Унаследованная проверка P03 и диапазон30/45/60; единый контролируемый параметр','30/45/60 — сценарии; норматив аэропорта/типа UNKNOWN','замыкание и время продажи обратного рейса','все расписания при turn30/45/60','P03/handling: минимальный наземный цикл по каждому аэропорту и типу')
 ass('03',8,'блок-ч/хвост/сутки','Для сопоставимости с диагностическим P03 выбран u8; BASE использовал10. Это ограничение проекта, не норматив экипажа.','8 и10 — контролируемые сценарии; реальный максимум UNKNOWN','нижняя необходимая оценка рабочих единиц','8/10; полная цепочка вместо деления часов','P03: экипажные задания, MRO, исправность, аэропортовые окна')
 ass('04',{'working_days':6,'ground_day':'Sunday'},'сутки/нед','Один свободный день оставлен для планирования ТО/переносов; не утверждение, что одного дня достаточно','0/1/2 дней ground в неделю — сценарии; действительный календарь UNKNOWN','конструктивная, не глобально минимальная когорта','сравнить 5/6/7 рабочих дней; открытый ground не обязательный MRO','P03: тип и программа ТО; фактические интервалы и окна')
 ass('05',1,'резервный самолёт на пакет','Контроль с выделенным резервом по P03; не правило4+1 и не вывод о свободном RW парке','R=0/1 или подтверждённый общий резерв; готовность/вероятность UNKNOWN','полная когорта2/3/4 для1/2/3 рабочих; стоимость резерва','R=0 только ветка с явной политикой восстановления; общий хвост нельзя считать дважды','P03: место/время реакции/совместные обязательства и стоимость')
 ass('06',{'core_frequency':3,'extension_frequency':2},'возвратов/направление/нед','3 для core даёт пн/ср/пт или вт/чт/сб и тест коротких поездок; 2 для добавок проверяет thin-service. Спрос эти частоты не доказал.','1/2/3/5 — экспериментальные варианты; оптимальная частота UNKNOWN','8/11 пар и полезные сроки поездок; LF не назначен','P05 пересчитывает те же спросовые пулы при частотах1/2/3/5','P05 по месяцу/дню/цели поездки с outside и действующими RW')
 ass('07',{'U1_start_SVX':'07:00','U2_start_SVX':'09:00','U3_start_SVX':'08:00'},'локальное время','Выбраны для замыкания базовых оборотов днём; слоты и коммерческая удобность не подтверждены','допустимое слот-окно UNKNOWN; тест сдвига ±120мин не разрешение','продукт и собственный переток','P05 сравнить retiming при неизменной частоте и затронутых стыковках','P03 слоты/curfew; P05 полезные окна/старые брони; P02 аэропортовый доступ')
 ass('08',{'seats_reference':100,'sold_journeys':None,'load_factor':None},'кресел/пассажиров','100 — семейный аналог текущего SSJ из P03, фактическая конфигурация и SJ100 RW UNKNOWN','SJ100 до103 у производителя; фактический payload/blocked seats UNKNOWN','номинальная геометрия кресел не открытый inventory','100/103 только явные калибруемые конфигурации; carry<=saleable seats; никакого demand=capacity','P03 хвост/engine/config; P05 demand/choice; load control по багажу')
 ass('09',{'demonstration_windows':['2027-01-11/2027-02-07','2027-05-10/2027-06-06','2027-07-12/2027-08-08','2027-10-11/2027-11-07','2028-01-10/2028-02-06','2028-05-08/2028-06-04','2028-07-10/2028-08-06','2028-10-09/2028-11-05'],'chain_control_anchors':['2028-12-11','2028-07-10']},'датированные проектные окна','28 дней дают проверки1/2/3/7/10/14 ночей в четырёх разных частях года. Для цепочек выбран отдельный декабрьский контроль и июль дляC17-S. Это сценарные даты, не опубликованное расписание','ежемесячный спрос/фактические сезоны UNKNOWN','год не выводится из одной недели; условия 24месяцев в programme_calendar','вне окна будущий календарь остаётся проектом; P05 нужен по всем24месяцам','P02/P03: настоящий календарь 2027/28; P05 сезонность и глубина продаж')
 ass('10',{'new_SJ_before_2027H2':0,'new_TU214':0},'новых бортов','Постановка кейса: SJ100 не раньше H2 2027. 0 новых Ту214 — обязательная самостоятельная ветка','N(t), ввод, экипажи/ТО и частичные/задержанные поставки UNKNOWN','нельзя запускать StageA-2027 winter как новыйSJ','поставлено≠введено≠доступно; ветви phased/partial/delayed/none','P03: принятый календарь каждого хвоста; не программа производства')
 ass('11',{'retiming':'replacement_not_addition','KEEP':'future_same_resource'},'политика P/KEEP','Опубликованные WZ5071/5072,1033/1034,1025/1026,5029/5030,1067/1068 и прочие RW не обнуляются. Перенос существующего борта требует донорского задания.','фактические продажи/донор/штрафы UNKNOWN','нет нового спроса от переименования рейса; полная delta unknown','сохранять фиксированные продажи; потеря стыковки/каннибализация','RW PNR/OD, план хвостов, interline, полный затронутый бизнес')
 ass('12',{'short_stay_nights':[1,2,3],'family_sanatorium_nights':[7,10,14]},'ночей','Проверочные сроки из исторических гипотез; платежеспособность и частоты пребывания неизвестны','распределение сроков/ценность времени UNKNOWN','только наличие обратной даты не полезность/защита поездки','нулевая/положительная доступность по каждому сроку; нет переноса агрегата турпотока в продажи','P05 реальные бронирования по цели, длительности, дню и поездке')
 ass('13',{'RGK_winter':'group_or_sport','RGK_summer':'leisure','MRV':'7/10/14 nights','MMK':'winter_optional'},'сезонное назначение продукта','Существующие RW RGK/MMK и исторические гипотезы; это продуктовые варианты, не доказанная месячная кривая спроса','объём/плательщик/контракт UNKNOWN','сезонная замена допускается, доход за закрытые месяцы не ноль по умолчанию','winter/summer/shoulder/off и одинаковый ресурс; цена смены','P05 туроператор/корпоративный плательщик без внешнего контакта; тариф с20кг и спецбагажом')
 ass('14',{'chain_geometry':'30 + 60*1.2*great_circle_km/750'},'мин/плечо','Формула BASE (0.5ч+трассовое расстояние/750); коэффициент1.2 выбран единым для экспериментальных цепочек без опубликованного аналога','1.1/1.2/1.3 и ±20% времени — сценарии; dispatch UNKNOWN','C09/10/14/15/17 нельзя допустить по геометрии','все плечи/turn/crew и обратная связь одновременно','P03 реальная трасса/летная эксплуатация; P04 топливо по полётному плану')
 ass('15',{'corporate_block_seats':None,'fare':None,'subsidy_future':None,'capture_coefficients':None},'кресел;RUB/поездку','Нет подтверждённого договора; P04 referencecosts не ставки2027/28. Единственный спрос/choice — P05.','UNKNOWN; нет выбранного доверительного интервала','экономика и ranking NOT_RUN','нулевой support как отдельная явная ветка; неизвестные расходы не0','P05 контракт/нетто-тариф/choice; P04 условия поддержки/ставки/оплата')
 ass('16',{'programme_mix':'U1 core + U2 comparative + U3 seasonal'},'набор программ','Покрывает существующие продажи, сильных конкурентов, обычные возвраты и сезонный/групповой продукт без принуждения треугольников','оптимум UNKNOWN; все ядра заменяемы в общем P06','приоритет запуска исследований, не выбор рынка по баллу','равный ресурс новым хабам/базам и пакетам; предельная единица отдельно','совместный расчёт P05/P06 с manifests всех программ')
 ass('17',{'RGK_geometry':'midpoint of runway thresholds','schedule_years':'2026/2027 inferred season'},'координаты; даты','RGK_TECH: опубликованные пороги02/20 усреднены только для геометрии; год в коротких датах таблицы SVX восстановлен как сезон2026/27 по контексту текущей публикации.','точнаяARP/явныйгод UNKNOWN; частота не переносится на2028','геометрический аналог C17-S и сезонный source export','проверить полный год/дни в primary dated source; координаты не dispatch','P03 ARP; P02 принять точные даты/исключения и конфликтующие номера WZ1053/5053')
 writec('assumptions.csv',A);writej('assumptions.json',A)

 # 11 конкретных прямых кандидатов; доступные поля исходного продукта сохраняются.
 names={'OMS':'Омск','KUF':'Самара','UFA':'Уфа','GOJ':'Нижний Новгород','KJA':'Красноярск','MRV':'Минеральные Воды','SGC':'Сургут','KZN':'Казань','VOG':'Волгоград','RGK':'Горно-Алтайск','MMK':'Мурманск'}
 links={'OMS':['C07','C31','C33','C35'],'KUF':['C09','C11','C16'],'UFA':['C10','C11'],'GOJ':['C32','C33','C35'],'KJA':['C07','C22'],'MRV':['C14','C15','C16','C31','C33'],'SGC':['C10'],'KZN':['C32'],'VOG':['C09'],'RGK':['C17','C18'],'MMK':['C17','C26']}
 signals={
  'OMS':'Существующий WZ5071/5072 и поздний вылет21:20; проверить дневное дополнительное окно против retiming без роста частоты. C07 не сохранял прежний возврат.',
  'KUF':'Существующий WZ1033/1034 и Utair UT281/282. Разница дневного и вечернего продукта измерима по расписанию; спрос на третью параллельную опцию не установлен.',
  'UFA':'Существующий WZ1025/1026 и Utair: P02 получил однодневные тарифные корзины на08.12.2026 и поздние периоды. Это лучший калибровочный рынок, не доказательство нового спроса.',
  'GOJ':'Существующие WZ5029/5030 в P02; дневное окно может изменить деловой и стыковочный продукт. Нужна проверка всех защищённых продаж.',
  'KJA':'FV6792/6800 и FV6791/6799 в неделе07–13.12.2026. P02 сохраняет67.1тыс за2025 только по группе Аэрофлот, это не общийOD. Прямой возврат — контрольC07.',
  'MRV':'U6 и SU в обе стороны в P02; действующие RW продажи/партнёрские пути через другие базы UNKNOWN. Санаторный продукт требует реальных обратных дат и общего тарифа.',
  'SGC':'Официальные WZ1017/1018 SVX–SGC уже наблюдаемы13.11.2026; P02 хранил промо-ссылку без полного расписания. Корпоративный блок не подтверждён.',
  'KZN':'Существующий ежедневный WZ1067/1068 в авторском срезе07–13.12.2026. Проверка события только сверх закреплённых продаж, без подмены годового спроса.',
  'VOG':'Y7-951/952 в P02; сравнить прямой возврат и обе ориентацииC09. Наличие конкурента не критерий отказа.',
  'RGK':'Первичные SVX и RGK публикуют WZ5053/5054 SSJ100 зимой2026/27; это изменение существующего продукта. Лыжный/спортивный багаж требует payload. Не считать весь Алтай новым рынком.',
  'MMK':'Первичное SVX расписание WZ5007/5008 зимой2026/27. Публикация даёт существующийRW продукт, не оплаченный северный туризм. Прямой возврат — контроль сезонной цепочкиC17.'}
 candidates=[]
 for n,e in enumerate(EPS,1):
  rr=[r for r in p02 if {r['origin'],r['destination']}=={'SVX',e}]
  pr=[r for r in primary if {r['origin'],r['destination']}=={'SVX',e}]
  mids=[r['market_id'] for r in coverage if {r['origin'],r['destination']}=={'SVX',e}]
  unit='U1' if e in ['OMS','KUF','UFA','GOJ'] else ('U2' if e in ['KJA','MRV','SGC','KZN'] else 'U3')
  freq=3 if unit=='U1' else 2
  candidates.append({'candidate_id':f'SVX-D{n:02d}','origin':'SVX','destination':e,'airport_pair':'-'.join(sorted(['SVX',e])),
   'title':f'Екатеринбург–{names[e]}: обычный возврат','programme_module':unit,'complete_path':f'SVX>{e}>SVX','legacy_ids':links[e],
   'signal':signals[e],'signal_status':'опубликованный/исторический продукт; размер доступного спроса UNKNOWN',
   'passenger_stay_test':'1/2/3/7/10/14 ночей: точные даты в passenger_stays.csv; часы на месте и аэропортовый доступ UNKNOWN',
   'alternatives':'KEEP действующие прямые RW/другие перевозчики; продаваемая пересадка через конкретный аэропорт при доказательстве; поезд/авто на ту же дату; отказ от поездки',
   'competitor_source_labels':sorted({r['carrier'] for r in rr if r['carrier']!='UNKNOWN'}|{r['carrier_source_label'] for r in pr}),
   'source_product_ids':[r['product_id'] for r in rr], 'source_row_hashes':[r['source_row_sha256'] for r in rr],
   'primary_record_ids':[r['record_id'] for r in pr],'primary_row_sha256':[r['row_sha256'] for r in pr],
   'source_periods':sorted({r['period'] for r in rr}|{r['validity_source_text']+' (2026/27 contextual)' for r in pr}), 'coverage':'PARTIAL; полный список конкурентов и кресла UNKNOWN; source export не admission',
   'proposed_returns_week':freq,'return_frequency_unit':'полный оборот; каждый направленный рейс имеет ту же частоту',
   'outbound_block_min':BM[e][0],'inbound_block_min':BM[e][1],'outstation_turn_min':45,'roundtrip_block_min':sum(BM[e]),
   'roundtrip_elapsed_min':sum(BM[e])+45,'aircraft_variant_branches':['RRJ95B/SaM146 exact tail pending','RRJ95LR/SaM146 exact tail pending','SJ100/PD8 analogue only pending'],
   'preserved_sales':'Все будущие действующие RW direct/through/partner/charter и фиксированные брони в KEEP; затрагиваемые переназначить один раз',
   'added_sales':'Только P05 allocation на добавленные датированные продукты; продажи от retiming не автоматически новые',
   'cut_sales':'UNKNOWN: отмена/смена времени старого рейса и потеря стыковок/донорских задач только по PNR и календарю',
   'demand_tariff_required':f'P05: directed SVX↔{e}; 24 месяца; purpose/stay/day; gross choice и net RUB/journey;20кг/спецбагаж; RW cannibalization; outside; response',
   'cost_driver_set':'CD01–CD17 в cost_drivers.csv','resource_formula':'sum(assigned directed block minutes); max concurrent tails; closed position; admitted crew/MRO/turn/slots; +reserve policy once',
   'slot_season_crew_MRO_gate':'UNKNOWN до P03; все начальные позиции новых/переносимых хвостов и ferry/cash должны быть добавлены',
   'status':'CONDITIONAL_STAGE_A_CANDIDATE','stage_b':'P05/P06 NOT_RUN','assumption_ids':[f'P08-SVX-A{i:02d}' for i in range(1,18)]})
 writec('direct_candidates.csv',candidates)
 writec('block_time_inputs.csv',[{'origin':'SVX','destination':e,'outbound_minutes':BM[e][0],'inbound_minutes':BM[e][1],
   'selected_basis':'Для OMS/KUF/KZN/VOG опубликованный BASE/P02 направленный аналог; UFA/GOJ часы P02; KJA/MRV другой реактивный тип P02; SGC/RGK/MMK первичная SVX-таблица 12.11.2026',
   'source_product_ids':[r['product_id'] for r in p02 if {r['origin'],r['destination']}=={'SVX',e} and r['elapsed_min_reported'] not in ['', 'UNKNOWN']],
   'primary_record_ids':[r['record_id'] for r in primary if {r['origin'],r['destination']}=={'SVX',e}],
   'future_type_cost_admitted':False,'range_scope':'0.9/1/1.2 выбранные стресс-множители, не доверительный интервал','assumption_ids':['P08-SVX-A01','P08-SVX-A17']} for e in EPS])

 # Шаблоны замкнуты в SVX; ground-day не подменяет ТО.
 U1={0:['OMS','UFA'],1:['KUF','GOJ'],2:['OMS','UFA'],3:['KUF','GOJ'],4:['OMS','UFA'],5:['KUF','GOJ']}
 U2={0:['KJA'],1:['MRV'],2:['SGC','KZN'],3:['KJA'],4:['MRV'],5:['SGC','KZN']}
 U3={0:['VOG'],1:['RGK'],2:['MMK'],3:['VOG'],4:['RGK'],5:['MMK']}
 U4={0:['MRV'],1:['KJA'],2:['OMS','UFA'],3:['MRV'],4:['KJA'],5:['KUF','GOJ']}
 U3season={0:['VOG'],1:['RGK'],2:[],3:['VOG'],4:['RGK'],5:[]}
 programmes=[
  {'programme_id':'SVX-KEEP','name':'Не использовать дополнительный ресурс в SVX','modules':[],'unique_pairs':0,'working_units':0,'dedicated_reserve_scenario':0,'status':'не отменяет существующую сеть; ресурс может остаться невведённым/на резерве/в иной программе; платежи по обязательствам сохраняются'},
  {'programme_id':'SVX-RET','name':'Изменить время существующего продукта','modules':['U1_RETIME'],'unique_pairs':4,'working_units':None,'dedicated_reserve_scenario':None,'status':'замены WZ на OMS/KUF/UFA/GOJ при неизменной будущей частоте KEEP; шаблон12возвратов не существующий assignment; число хвостов до/после UNKNOWN'},
  {'programme_id':'SVX-U1','name':'Четыре направления на первой рабочей единице','modules':['U1'],'unique_pairs':4,'working_units':1,'dedicated_reserve_scenario':1,'status':'промежуточная ступень; частоты3/нед на4парах; не финальные8–12'},
  {'programme_id':'SVX-U12','name':'Восемь направлений на двух рабочих единицах','modules':['U1','U2'],'unique_pairs':8,'working_units':2,'dedicated_reserve_scenario':1,'status':'maincase кандидат конец2028; core3/нед, KJA/MRV/SGC/KZN2/нед; при допуске ресурса'},
  {'programme_id':'SVX-U123','name':'Одиннадцать направлений на трёх рабочих единицах','modules':['U1','U2','U3'],'unique_pairs':11,'working_units':3,'dedicated_reserve_scenario':1,'status':'сезонный портфель; зимойMMK, летом/межсезоньеMMK-off как отдельный вариант; закрытие не означает нет спроса'},
  {'programme_id':'SVX-U1234','name':'Одиннадцать направлений при общей когорте пять','modules':['U1','U2','U3','U4'],'unique_pairs':11,'working_units':4,'dedicated_reserve_scenario':1,'status':'контроль с теми же условными 4рабочими+1резерв, что в диагностикеP03. U4 добавляет частоты на уже выбранных парах; спрос и четвёртая единица не предрешены. Альтернатива — U123+один idle с теми же обязательствами'},
 ]
 module_maps={'U1':U1,'U2':U2,'U3':U3,'U4':U4}
 module_bh={k:sum(sum(BM[e]) for es in v.values() for e in es)/60 for k,v in module_maps.items()}
 for p in programmes:
  p.update(aircraft_cost_variant='SSJ100 и SJ100/ПД8 раздельно; 0новыхТу214',fleet_scope='тот же P03 admitted fleet и календарь в P/KEEP и хабах',
    existing_RW_keep='полный затронутый будущий бизнес; не историческая сеть2025 и не пустойKEEP',
    data_acceptance='research_design_only_NOT_P06_READY',monthly_horizon='2027-01/2028-12',
    cash_need=None,profit=None,passengers=None,market_share=None,assumption_ids=[a['assumption_id'] for a in A])
  p['weekly_block_hours_reference']=sum(module_bh[k] for k in p['modules'] if k in module_bh) if p['programme_id']!='SVX-RET' else None
  p['conditional_cohort_with_dedicated_reserve']=p['working_units']+p['dedicated_reserve_scenario'] if p['working_units'] is not None else None
  p['minimum_conditional_cohort_scope']='конструктивная когорта этого шаблона; не оптимум по всем расписаниям; реальный RW UNKNOWN'
  p['opportunity_cost']='сравнить тот же новый хвост в лучшем альтернативном хабе/базе/прямом пакете; для existing tail дополнительно потерянный donor; не складывать результаты независимых моделей'
 writej('programme_candidates.json',{'schema':'P08-SVX-research-stage-A-v1','as_of':'2026-11-12','producer_contract_pin':PINS['P06'],
  'producer_contract_state':'P06 executable conditional engine; independent acceptance pending; toy data not RW; этот файл не executable bundle',
  'programmes':programmes,'module_weekly_block_hours_reference':module_bh,'module_weekdays_iso':{k:{str(d+1):es for d,es in v.items()} for k,v in module_maps.items()},
  'selection_basis':'U1 сохраняет видимость действующих коротких RW рынков и контроль retiming; U2 вводит длинный конкурентныйKJA, санаторныйMRV и северныйSGC; U3 проверяет сезонные расходы и11пар. Это набор экспериментов, не ранжирование по прибыли.',
  'mutual_exclusion':'KEEP/RET/U1/U12/U123 — альтернативы, U12 включаетU1, U123 включаетU12; не суммировать продажи/деньги и резерв между альтернативами',
  'do_not_infer':['существующий свободный парк','готовность экипажей/ТО','открытые кресла конкурентов','выручку/прибыль','победу над хабами','достижение№2']})
 resource_rows=[]
 for p in programmes:
  bh=p['weekly_block_hours_reference'];active=p['working_units']
  resource_rows.append({'programme_id':p['programme_id'],'winter_weekly_block_hours_reference':bh,
   'necessary_working_units_hours_only_u8_7days':math.ceil(bh/56) if bh is not None else None,
   'constructive_working_units':active,'selected_reserve_policy_units':p['dedicated_reserve_scenario'],
   'selected_total_cohort':p['conditional_cohort_with_dedicated_reserve'],
   'available_cohort_actual':None,'entry_gate':'N_available(t) >= working(t)+reserve(t), после допуска позиции, crew, MRO и прежних задач; один хвост не бывает одновременно в двух программах',
   'five_tail_common_control':'При условной C=5,R=1: KEEP/альтернативное использование; U123=3работают+1резерв+1невыделенный; U1234=4работают+1резерв. Обязательства по всем5 сохраняются вP/KEEP.',
   'minimum_scope':'Часовая нижняя граница необходима; конструкция совпадает дляU1/U12/U123 вреференсе. Это не операционный минимум RW. ДляU1234 глобальный минимум не доказан.',
   'donor_or_next_use':'Для existing — точный donor_task_id и потерянный результат; для new — лучшая допустимая альтернативная программа; для idle — committed payments, хранение/резерв/выход',
   'assumption_ids':['P08-SVX-A01','P08-SVX-A03','P08-SVX-A04','P08-SVX-A05','P08-SVX-A10','P08-SVX-A11']})
 writec('resource_cohorts.csv',resource_rows)

 windows=[]
 for y,starts in [(2027,['01-11','05-10','07-12','10-11']),(2028,['01-10','05-08','07-10','10-09'])]:
  for season,s in zip(['winter','shoulder_spring','summer','shoulder_autumn'],starts):
   windows.append((f'{y}-{season}',dt.date.fromisoformat(f'{y}-{s}'),season))
 flights=[];rotations=[];days=[]
 def stamp(x):return x.isoformat().replace('+00:00','Z')
 for p in programmes[2:]:
  for wid,start,season in windows:
   for day in range(28):
    date=start+dt.timedelta(days=day)
    for mod in p['modules']:
     es=module_maps[mod].get(date.weekday(),[])
     # MMK сезонный модуль используется зимой; в прочие окна отдельные ground/inactive дни.
     if mod=='U3' and season!='winter':es=U3season.get(date.weekday(),[])
     local_hour={'U1':7,'U2':9,'U3':8,'U4':7}[mod]
     cur=dt.datetime.combine(date,dt.time(local_hour),tzinfo=dt.timezone(dt.timedelta(hours=5))).astimezone(dt.timezone.utc)
     begin=cur;block=0;tail=p['programme_id']+'-'+mod;daily_ids=[]
     for seq,e in enumerate(es):
      rid=f'{p["programme_id"]}-{wid}-{date}-{mod}-{seq+1}'
      rb=cur;ids=[]
      for leg,(a,b,mins) in enumerate([('SVX',e,BM[e][0]),(e,'SVX',BM[e][1])],1):
       end=cur+dt.timedelta(minutes=mins);fid=rid+f'-L{leg}'
       flights.append({'flight_instance_id':fid,'programme_id':p['programme_id'],'window_id':wid,'rotation_id':rid,'scenario_unit_id':tail,
         'origin_airport':a,'destination_airport':b,'departure_utc':stamp(cur),'arrival_utc':stamp(end),
         'departure_local':cur.astimezone(dt.timezone(dt.timedelta(hours=OFF[a]))).isoformat(),
         'arrival_local':end.astimezone(dt.timezone(dt.timedelta(hours=OFF[b]))).isoformat(),
         'block_minutes':mins,'calendar_status':'предлагаемый диагностический шаблон; не факт2027/28','seat_inventory_usable':False,
         'aircraft_variant':'RRJ95_family_analogue; SJ100_PD8 отдельная не допущенная ветвь','crew_id':None,'maintenance_admission':None,'airport_slots':None,
         'source_refs':f'BM:{e};P02_products_selected.csv;live_fetch_receipts.json', 'assumption_ids':['P08-SVX-A01','P08-SVX-A02','P08-SVX-A07','P08-SVX-A08','P08-SVX-A09']})
       ids.append(fid);daily_ids.append(fid);block+=mins;cur=end+dt.timedelta(minutes=45)
      rotations.append({'rotation_id':rid,'programme_id':p['programme_id'],'window_id':wid,'date_at_SVX':date.isoformat(),'scenario_unit_id':tail,
       'path':f'SVX>{e}>SVX','start_utc':stamp(rb),'last_arrival_utc':stamp(cur-dt.timedelta(minutes=45)),
       'flight_ids':ids,'block_minutes':sum(BM[e]),'elapsed_minutes':sum(BM[e])+45,'final_position':'SVX','positioning_flights':0,
       'positioning_scope':'оба концаSVX по построению; реальное начальное положение нового/перенесённого хвоста UNKNOWN',
       'crew_MRO_reserve_status':'UNKNOWN; механическое замыкание не эксплуатационный допуск'})
     days.append({'programme_id':p['programme_id'],'window_id':wid,'date':date.isoformat(),'unit_id':tail,'returns':es,
       'block_minutes':block,'elapsed_minutes':int((cur-dt.timedelta(minutes=45)-begin).total_seconds()/60) if es else 0,
       'start_position':'SVX','end_position':'SVX','planned_status':'flight_template' if es else 'ground_unspecified_not_MRO_proof','flight_ids':daily_ids})
 writec('dated_templates/flights.csv',flights);writec('dated_templates/rotations.csv',rotations);writec('dated_templates/aircraft_days.csv',days)
 retime=[]
 for f in flights:
  if f['programme_id']=='SVX-U1' and f['window_id']=='2028-winter' and '2028-01-10'<=f['departure_local'][:10]<='2028-01-16':
   ep=f['destination_airport'] if f['origin_airport']=='SVX' else f['origin_airport']
   retime.append({'action_id':'RET:'+f['flight_instance_id'],'action':'REPLACE_CLOCK_ONLY_IF_MATCHED_KEEP_FLIGHT',
    'proposed_departure_utc':f['departure_utc'],'proposed_arrival_utc':f['arrival_utc'],
    'origin':f['origin_airport'],'destination':f['destination_airport'],'return_rotation':f['rotation_id'],
    'matched_future_KEEP_flight_id':None,'old_published_reference_ids':[r['product_id'] for r in p02 if r['origin']==f['origin_airport'] and r['destination']==f['destination_airport'] and r['carrier']=='WZ'],
    'guard':'Без совпавшего KEEP-flight действие HOLD. Нельзя добавлять эти рейсы, удалять остаток KEEP-частоты или считать прежние продажи нулём. Все невыбранные рейсы KEEP остаются.',
    'binding_status':'FUTURE_KEEP_UNKNOWN','sales_to_preserve':'PNR, through, partner, connection, fixed contracts; reaccommodation costs UNKNOWN',
    'assumption_ids':['P08-SVX-A07','P08-SVX-A11']})
 writec('dated_templates/retiming_actions.csv',retime)
 # Предлагаемые цепочки — отдельные конкретные контроли исторических гипотез.
 def gc(a,b):
  x,y=coord[a],coord[b];p1,p2=map(math.radians,(x[0],y[0]));dp=p2-p1;dl=math.radians(y[1]-x[1])
  return 6371*2*math.asin(min(1,math.sqrt(math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2)))
 bref={(r['origin'],r['destination']):int(float(r['minutes'])) for r in blockrefs}
 def bm(a,b):
  if a=='SVX' and b in BM:return BM[b][0],'P08-SVX-A01'
  if b=='SVX' and a in BM:return BM[a][1],'P08-SVX-A01'
  if (a,b) in bref:return bref[a,b],'P08-SVX-A01'
  return math.ceil((30+60*1.2*gc(a,b)/750)/5)*5,'P08-SVX-A14'
 controls=[
  ('C07-R','C07',['SVX','OMS','KJA','OMS','SVX'],'Сравнить с отдельнымиSVX–OMS–SVX иSVX–KJA–SVX; сохранить прежнийWZ5072/продажи/домашнее положение'),
  ('C09-A','C09',['SVX','KUF','VOG','SVX'],'Две ориентации в разные дни; треугольник не даёт обратныйKUF–VOG тем же рейсом'),
  ('C09-B','C09',['SVX','VOG','KUF','SVX'],'Совместно сC09-A и обычными прямыми возвратами; не три независимых продажи одного кресла'),
  ('C10-A','C10',['SVX','UFA','SGC','SVX'],'Корпоративный блок только при договоре; KEEP WZ1017/1018 иWZ1025/1026'),
  ('C10-B','C10',['SVX','SGC','UFA','SVX'],'Обратная ориентация; разные цели по дням; объём контракта UNKNOWN'),
  ('C14-R','C14',['SVX','KVX','MRV','KVX','SVX'],'Санаторные7/10/14ночей; frozen input001UNKNOWN иinput002 exactreturn не переписываются'),
  ('C15-R','C15',['SVX','PEE','MRV','PEE','SVX'],'Сравнить с прямымPEE–MRV, подвозомPEE–SVX ипрямымSVX–MRV; короткий участок не отказ'),
  ('C16-R','C16',['SVX','KUF','MRV','KUF','SVX'],'Калибровочный существующийKUF–MRV; не переносить егоOD наKVX'),
  ('C17-W','C17',['SVX','PEE','MMK','PEE','SVX'],'Зимний продукт отдельно; прямойSVX–MMK — реальная исходная продажа'),
  ('C17-S','C17',['SVX','PEE','RGK','PEE','SVX'],'Летний продукт отдельно; считать смену/старт/багаж; прямойSVX–RGK сохраняется'),
  ('C11-UFA','C11',['SVX','UFA','NUX','UFA','SVX'],'Изменение существующегоUFA–NUX; не новый независимый спрос; точныеWZ1081/1082 UNKNOWN'),
  ('C11-KUF','C11',['SVX','KUF','NUX','KUF','SVX'],'В официальном табло13.11.2026 ужеWZ5303/5304; сохранитьKUF–NUX вKEEP'),
 ]
 control_legs=[];control_sum=[]
 for i,(cid,legacy,path,note) in enumerate(controls):
  wdays=[1] if cid.endswith('-A') else ([4] if cid.endswith('-B') else [1,4])
  date=dt.date(2028,7,10) if cid=='C17-S' else dt.date(2028,12,11)
  date+=dt.timedelta(days=(wdays[0]-1-date.weekday())%7)
  cur=dt.datetime.combine(date,dt.time(3),tzinfo=dt.timezone.utc);begin=cur;blocks=0;ids=[]
  for k,(a,b) in enumerate(zip(path,path[1:]),1):
   minutes,aid=bm(a,b);end=cur+dt.timedelta(minutes=minutes);fid=cid+f'-{k}'
   control_legs.append({'control_id':cid,'legacy_id':legacy,'flight_instance_id':fid,'origin':a,'destination':b,'departure_utc':stamp(cur),'arrival_utc':stamp(end),
     'block_minutes':minutes,'next_turn_minutes':45 if k<len(path)-1 else 0,'assumption_id':aid,'status':'условный контроль; crew/ТО/слоты/продажи UNKNOWN'})
   blocks+=minutes;ids.append(fid);cur=end+dt.timedelta(minutes=45)
  control_sum.append({'control_id':cid,'legacy_id':legacy,'path':'>'.join(path),'date':date.isoformat(),'flight_ids':ids,'block_minutes':blocks,
   'proposed_weekdays_iso':wdays,'frequency_scope':'повторение цепочки в каждом выбранном дне; годовой календарь и месячные условия UNKNOWN; A/B вместе дают обратную ориентацию',
   'weekly_block_hours':blocks*len(wdays)/60,'minimum_working_hours_only':math.ceil(blocks*len(wdays)/(8*60*7)),
   'elapsed_minutes':int((end-begin).total_seconds()/60),'position_closed':'SVX','daily_u8_exceeded':blocks>480,
   'disposition':'CONDITIONAL; пересобрать частоту/ночёвку/экипажи при превышенииu8; не экономический отказ','comparison':note,
   'crew_turn_MRO_reserve':'UNKNOWN; ночёвка и смена экипажа могут изменить ресурс/затраты','assumption_ids':['P08-SVX-A01','P08-SVX-A02','P08-SVX-A03','P08-SVX-A14']})
 writec('dated_templates/historical_chain_legs.csv',control_legs);writec('dated_templates/historical_chain_controls.csv',control_sum)

 # Проверяем точные обратные даты; это не вероятность покупки и не гарантия полезного времени.
 index=defaultdict(set)
 for f in flights:
  index[(f['programme_id'],f['origin_airport'],f['destination_airport'])].add(f['departure_local'][:10])
 stayrows=[]
 for p in programmes[2:]:
  for e in EPS:
   dates=sorted(index[p['programme_id'],'SVX',e])
   for d in dates:
    for nights in [1,2,3,7,10,14]:
     back=dt.date.fromisoformat(d)+dt.timedelta(days=nights)
     # Не смешиваем разные демонстрационные окна и не записываем0за пределами28дней.
     win=next((w for w in windows if w[1]<=dt.date.fromisoformat(d)<w[1]+dt.timedelta(days=28)),None)
     within=back<win[1]+dt.timedelta(days=28)
     status=('exact_date_present' if back.isoformat() in index[p['programme_id'],e,'SVX'] else 'no_return_in_this_template') if within else 'outside_capture_UNKNOWN'
     stayrows.append({'programme_id':p['programme_id'],'market':f'SVX>{e}>SVX','outbound_date':d,'nights':nights,'required_return_date':back.isoformat(),
       'return_status':status,'meaning':'только календарная возможность; fare/inventory/protection/purpose/ground UNKNOWN','assumption_id':'P08-SVX-A12'})
 writec('dated_templates/passenger_stays.csv',stayrows)

 # Все24месяца явны. Пустота рынка/ставки не заменяется нулём.
 monthly=[]
 for y in [2027,2028]:
  for m in range(1,13):
   end=calendar.monthrange(y,m)[1]
   for p in programmes:
    for delivery in ['phased','partial','delayed','none']:
     monthly.append({'month':f'{y}-{m:02d}','programme_id':p['programme_id'],'delivery_branch':delivery,'calendar_days':end,
       'new_SJ_eligible_by_case':not(y==2027 and m<7),'new_TU214_count':0,
       'physical_available_cohort':None,'actual_entry_date':None,'existing_tail_donor':None,
       'activation_rule':'Только послеP03 service_entry/position/crew/MRO/reserve исовместногоP05/P06; none:нет новогоSJ, existing перенос только сдонором',
       'season_product':'winter_candidate' if m in [11,12,1,2,3] else ('summer_candidate' if m in [6,7,8] else 'shoulder_candidate'),
       'monthly_demand':None,'net_fare':None,'economics':None,'cash':None,'scope':'24месяца, а не умножение одной недели','assumption_ids':['P08-SVX-A09','P08-SVX-A10','P08-SVX-A13']})
 writec('programme_calendar.csv',monthly)

 costs=[
 ('CD01','physical_flight','fuel uplift tonnes + tankering + flight plan burn','fuel_contract_future;fuel_burn_SJ100_PD8','загрузка/цикл/погода/маршрут; SSJиПД8 отдельно'),
 ('CD02','physical_flight','MTOW; departures/arrivals; airport service units','airport handling/security/landing','SVXикаждыйendpoint; published reference неfuturecontract'),
 ('CD03','physical_flight','navigation route/weight/distance units','navigation','реальная трасса и действующие сборы'),
 ('CD04','journey_and_station','departing passengers; luggage; catering; distribution','passenger_service;distribution','сквозной тариф один раз; плечи расходуюткресла'),
 ('CD05','aircraft_and_cycle','block hours/cycles/calendar wear','MRO;engine reserves','дополнительноеобслуживание иpayments; reserve не дваждыexpense/cash'),
 ('CD06','crew','duty/flight/standby hours; headcount; hotels/travel','crew;training','FAP/roster; длиннаяцепочка не одна бесплатнаясмена'),
 ('CD07','base_station','avoidable incremental fixed station/tail/headcount months','base;maintenance station','SVX existing station не значит marginal fixedcost=0; не повторятьсunkcost'),
 ('CD08','aircraft_cohort','tail/calendar months and actual contract obligations','aircraft_use;lease;insurance','стоимостьввода иобязательныеплатежи ивKEEP/idle; SSJ/SJ/TU отдельно'),
 ('CD09','reserve','tail months; availability; positioning; recovery events','reserve;disruption','общийрезервидентификатор один; время доoutstation'),
 ('CD10','launch_switch','training; certification; sales; deposits; seasonal switching','startup','групповойпродукт иretiming имеют изменениепродаж/договоров'),
 ('CD11','old_sales_and_donor','lost net contributions + reaccommodation/refunds + foregone contracts','prior tasks;self cannibalization','KEEP direct/through/partner/charter сохраняются; не дважды lost revenue иlost contribution'),
 ('CD12','support','eligible actual legs/passengers; limits; recognition; payment date','support_terms;support_event_map','2026 eligibility неfuturegrant; отдельнаяветка0поддержки'),
 ('CD13','cash_timing','ticket receipts; advances; deposits; vendor payment terms; refunds','cash_rules','начисление неreceipt; суммафинансирования иостаточныеобязательства'),
 ('CD14','tax_finance','tax; interest; debt; depreciation; FX price year','finance_reference;P06 accounting_policy','полныйоперационныйрезультат иcashраздельно; principal неoperatingexpense'),
 ('CD15','exit','cancellation; termination; customer obligations; reposition','exit','решениеstop не отменяет действующиеобязательства'),
 ('CD16','corporate_group','reserved seats; release date; block payment; penalties','contracts','числокорпоративныхработников/туристов не контракт; неперепродатьblockedseats'),
 ('CD17','next_resource','best feasible foregone new-tail programme; existing donor separately','P06 joint resource allocation','предельнаяединица пересчитываетсясовместно; differenceoftotals не суммаisolatedmodelprofits')]
 writec('cost_drivers.csv',[{'cost_driver_id':i,'owner':o,'quantity_driver':q,'P04_binding':b,'guard':g,'rate_2027_2028':None,'project_quantity':None,'KEEP_quantity':None,'missing_rate_is_zero':False,'assumption_ids':['P08-SVX-A11','P08-SVX-A15']} for i,o,q,b,g in costs])
 writec('evidence/P04_cost_component_index.csv',[r for r in budgets if any(t in r['component'].lower() for t in ['fuel','crew','reserve','base','startup','exit','lease','distribution','mro','airport','insurance'])])

 comparisons=[]
 specs=[
 ('CR01','P05','SVX-RET vs KEEP','Те же датированные частоты и физические рейсы; изменить только часы. Сохранить старые PNR, transit, partner, baggage; отделить новые поездки от перераспределения.','net_delta_journeys;lost_products;gross/net fare;time;choice'),
 ('CR02','P05','SVX-U1/U12/U123/U1234','Единый спросовой pool по конечному OD, месяцу, цели и сроку. Точные обратные даты; outside/rail/auto/competitor; все 24 месяца; booking_lead/as_of/date.','potential_travel;calibration;uncertainty;not capacity_as_demand'),
 ('CR03','P03','все программы','Привязать каждый flight instance к хвосту и варианту, initial position, crew, ТО, слотам, резерву и donor. Проверить все 28-дневные окна и итоговый календарь.','admitted fleet_calendar/assignments;hold reasons'),
 ('CR04','P04','все программы и KEEP','CD01–17: драйверы физических событий и поездок. Принять будущие ставки/диапазоны с assumption IDs, полное покрытие затрат и сроки оплаты.','P04 economic_events/cash_events; branch support=0'),
 ('CR05','P06','SVX-U12/U123/U1234 vs NEW_HUB/NEW_BASE/MIX','Одинаковые fleet_scope, delivery/external/cost/market/choice versions и future KEEP. Отдельно сравнить малую общую когорту и контроль C=5,R=1: U123+idle, U1234, hub/base/mixed. Общие OD, кресла, контракты и базы считаются один раз.','24 monthly;journeys/segments;full incremental;company funding;8–12 pairs'),
 ('CR06','P06','U1234 vs U123; U123 vs U12; U12 vs U1; U1 vs idle','Предельный новый хвост и пакет пересчитываются совместно. Старый донор и потеря его работы отдельно. Резерв имеет один owner ID; новый SJ вводится только по P03.','delta objective + displaced next-best programme + funding; global winner UNKNOWN'),
 ('CR07','P05/P06','C07/C09/C10/C14/C15/C16/C17/C11 controls','Обычные возвраты и цепочки: полный путь, направленные кресла, поездка и тариф один раз; две ориентации и полезные возвраты. Превышение выбранного u8 не экономический отказ.','control alternatives;old sales;inventory;crew;cost;conditional result'),
 ('CR08','P05','сезонный, корпоративный и событийный модули','Нужны точные даты, плательщик, объём, bag/payload, release/cancel. Событие 2028 UNKNOWN; разовый пик не превращать в годовой спрос.','contract or UNKNOWN; shoulder/off; switching cost'),
 ('CR09','P02','новая первичная информация SVX','Принять наблюдения WZ1017/1018,5053/5054,5007/5008 и отдельные carrier labels/codeshares. Не создавать физические дубли. Сохранить конфликты номера рейса и дат с P02.','source row extraction/year/day acceptance; open seats UNKNOWN'),
 ('CR10','P05/P06','C27/C35 ground/partner feeder','CEK/KRO/MQF или IJK/KRO→SVX: тот же journey pool; время наземного доступа, защита, стыковки и through fare. MQF canonical HOLD сохраняется.','optional product, not new air capacity; cash; interline contract'),
 ('CR11','P06','phased/partial/delayed/none; 0 новых Ту214','Применять принятый N(t), не график производства. До H2 2027 новые SJ=0. Неактивный борт и обязательные lease/донорские платежи сохранять в KEEP.','24 monthly scenarios;shortfall;adaptation dates/commitments'),
 ('CR12','P06','fixed vs adaptive','Сначала фиксированный дизайн; изменения по наблюдаемым фактам, времени и обязательствам. Траектория результата, финансирование и условия остановки без подгонки спроса.','stop/scale thresholds from calibrated costs; no invented LF threshold')]
 for i,owner,variants,request,out in specs:
  comparisons.append({'request_id':i,'owner':owner,'variants':variants,'request':request,'required_output':out,'status':'STAGE_B_PENDING_DEPENDENCY_NOT_ECONOMIC_REJECTION','source_pins':PINS,'assumption_ids':['P08-SVX-A11','P08-SVX-A15','P08-SVX-A16']})
 writec('comparison_requests.csv',comparisons)

 dispositions=[]
 actions={
 'C07':('SVX-D01;SVX-D05;C07-R','Оценена частичная механика; дальше условна','Frozen +270 block min и donor UNKNOWN сохранены. C07-R — новый контроль с другим аналогом времени; обычные два возврата — конкретная альтернатива. По одному расписанию не отвергать все цепочки.'),
 'C09':('SVX-D02;SVX-D09;C09-A;C09-B','Объединена в контролируемое сравнение','Обе ориентации заданы; прямые KUF/VOG в U1/U3. Треугольник не даёт обратный межгородской рейс тем же самолётом в тот же день.'),
 'C10':('SVX-D03;SVX-D07;C10-A;C10-B','Условна конкретным неизвестным','WZ1017/1018 уже есть. Корпоративный блок требует договора; годовой контракт и датированный платёжеспособный спрос UNKNOWN.'),
 'C11':('C11-UFA;C11-KUF;SVX-RET','Условна конкретным неизвестным','WZ5303/5304 опубликованы на 13.11.2026. Existing UFA/KUF–NUX сохранять в KEEP; перенос из SVX требует прежнего задания и потерь.'),
 'C14':('C14-R;SVX-D06','Условна конкретным неизвестным','Дана цепочка KVX и прямой контроль MRV. Frozen UNKNOWN и полезные возвраты не переписаны; санаторный плательщик, цена и спрос UNKNOWN.'),
 'C15':('C15-R;SVX-D06;C27','Условна конкретным неизвестным','Пермь сохранена; 500 км не экономический отказ. Сравнить PEE direct/ground SVX с местным рынком, доступом и донорским заданием.'),
 'C16':('C16-R;CR07','Сохранена калибровочным контролем','KUF–MRV не новый доказанный спрос; годовой агрегат не нормирует KVX/PEE или санаторный сегмент.'),
 'C17':('C17-W;C17-S;SVX-D10;SVX-D11','Объединена сезонным сравнением','Зима и лето отдельно; прямые SVX существуют. Стоимость смены продукта должна пройти общий P04/P06. Блок-часы не экономический отказ.'),
 'C18':('SVX-D10;SVX-U123','Условна конкретным неизвестным','Дан прямой возврат с аналогом 160/175 минут. Спецбагаж, payload и оплаченный групповой блок UNKNOWN. Существующие продажи RW сохранять в KEEP.'),
 'C22':('SVX-D05;CR07','Связь сохранена; собственная ветвь НЕВЫПОЛНЕНА P08','SVX–KJA не проверяет IKT–UUD–HTA/BAX–HTA. Исторический RW BAX–HTA остаётся в KEEP. Передать владельцу P07/P09; незавершённость не экономический отказ.'),
 'C26':('SVX-D11;CR07','Связь сохранена; собственная ветвь НЕВЫПОЛНЕНА P08','SVX–MMK не проверяет SCW–ARH–MMK. Спрос, поддержка и северные пары требуют отдельной работы; передать владельцу северной ветви.'),
 'C27':('SVX-U12;CR10','Условна конкретным неизвестным','Подвоз к SVX — опция конечной поездки, не авиасегмент. MQF canonical HOLD сохраняется; договорные цены и датированный календарь UNKNOWN.'),
 'C31':('SVX-U1/U12/U123/U1234;CR06;CR11','Переформулирована в ресурсный контроль','Новый SJ или замена типа не высвобождают SSJ автоматически. Ветвь 0 новых Ту214 сохранена. Existing tail требует donor; новый tail — лучшего альтернативного применения.'),
 'C32':('SVX-D04;SVX-D08;CR08','Условна конкретным неизвестным','GOJ/KZN уже имеют RW. Событие и плательщик 2027/28 UNKNOWN. Датированный блок с возвратом через 1/2/3 ночи — отдельная надстройка, не годовой спрос.'),
 'C33':('SVX-RET;CR01','Оценена дизайном; Stage B условна','Смена часов при сохранении частоты KEEP. Затронуты старые продажи и стыковки; будущие donor/PNR UNKNOWN. Существующие flight instances не удваиваются.'),
 'C34':('SVX-KEEP;CR03;CR06','Условна конкретным неизвестным','R=1 — контроль; общий резерв учитывается один раз. Позиционирование и восстановление UNKNOWN; число публикаций Ковра не вероятность нарушения.'),
 'C35':('SVX-D01;SVX-D04;CR10','Условна конкретным неизвестным','Фидер IJK/KRO не увеличивает физические кресла. Маркетинговый код не подтверждает договор; through/partner продажи сохранять в KEEP.')}
 legacy={r['candidate_id']:r for r in plan['legacy_hypotheses']}
 for cid,(desc,disposition,why) in actions.items():
  r=legacy[cid];dispositions.append({'legacy_id':cid,'original_title':r['title'],'original_paths':r['author_paths'],'ancestor_ids':r['ancestor_ids'],
    'original_checked_scope':r['checked_result_and_scope'],'descendant_ids':desc,'stage_A_disposition':disposition,'evidence_and_boundary':why,
    'economic_verdict':'NOT_RUN; экономический отказ и прибыль не установлены','review_condition':'Принятые P03/P04/P05 + совместный P06; источник/контракт по CR','source_commit':PINS['PLAN']})
 for cid,title,desc,why in [('SVX-N01','Обычные прямые возвраты при равном ресурсе','SVX-U1/U12/U123/U1234','Проверка альтернативы историческим цепочкам; восемь/одиннадцать пар к концу2028'),('SVX-N02','Неиспользование ресурса и отложенный ввод','SVX-KEEP','Контроль с обязательными платежами, резервом и альтернативной программой'),('SVX-N03','Предельная единица в SVX','CR06','Отдельно ценность U2 к U1, U3 к U12, U4 к U123; другое применение общего борта пересчитывается совместно')]:
  dispositions.append({'legacy_id':cid,'original_title':title,'descendant_ids':desc,'stage_A_disposition':'Новая условная гипотеза по данным','evidence_and_boundary':why,'economic_verdict':'NOT_RUN','review_condition':'P05/P06','source_commit':PINS['BASE']})
 writec('hypothesis_dispositions.csv',dispositions)

 # Реальные источники — provenance и границы рядом, без вымышленных диапазонов.
 receipts=json.loads((ROOT/'evidence/live_fetch_receipts.json').read_text())
 sources=[]
 for r in receipts:
  sources.append({'source_id':r['source_id'],'url':r['url'],'organization':'АэропортКольцово' if r['source_id'].startswith('SVX') else ('АэропортГорно-Алтайск' if r['source_id'].startswith('RGK') else 'Red Wings'),
   'publication_date':'UNKNOWN','retrieved_at':r['retrieved_at'],'period':'2026-11/2027-03; точныйпериодвстрокахрасписания' if 'SVX' in r['source_id'] or 'RGK' in r['source_id'] else 'текущиепродажи/табло11–13.11.2026;акция10–12.11.2026',
   'unit':'локальныечасы;даты;carrier/flight/type;promofareRUB' ,'granularity':'опубликованноепредложение/правилорасписания;неopeninventory',
   'status':r['status'],'coverage':'толькорелевантныйтекст;конкуренты/продажинеполны;расписаниене2028','sha256':r.get('raw_sha256'),'receipt':'evidence/live_fetch_receipts.json'})
 for r in p02:
  sources.append({'source_id':r['product_id'],'url':r['source_url'],'organization':'источникP02:'+r['source_id'],'publication_date':'UNKNOWN','retrieved_at':r['retrieved_at'],'period':r['period'],'unit':r['unit'],'granularity':r['row_grain'],
   'status':r['status'],'coverage':r['coverage'],'sha256':r['source_row_sha256'],'receipt':'evidence/P02_products_selected.csv'})
 writec('sources.csv',sources);writej('source_pins.json',{'pins':PINS,'input_files':INPUTS,'source_row_hash_method':'SHA256 canonical JSON original CSV data row, UTF8, sort_keys=True, separators comma-colon; csv_record_number is data record, not physical line for multiline CSV'})
 writec('source_rows.csv',SOURCE_ROWS)
 # Ресурсные арифметические/календарные проверки: ограничения этих checks явны.
 checks=[]
 def ck(name,ok,evidence,scope='механикапроекта;неadmission'):checks.append({'check':name,'pass':bool(ok),'evidence':evidence,'scope':scope})
 ck('endpoint_target_8_11',programmes[3]['unique_pairs']==8 and programmes[4]['unique_pairs']==11,'U12=8,U123=11 уникальныхнеориентированныхairportpairs')
 ck('all_rotations_close_at_SVX',all(r['final_position']=='SVX' for r in rotations),len(rotations))
 bytail=defaultdict(list)
 for f in flights:bytail[f['scenario_unit_id'],f['window_id']].append(f)
 overlap=[];position=[];turns=[]
 for k,rs in bytail.items():
  rs.sort(key=lambda r:r['departure_utc'])
  for a,b in zip(rs,rs[1:]):
   gap=(dt.datetime.fromisoformat(b['departure_utc'].replace('Z','+00:00'))-dt.datetime.fromisoformat(a['arrival_utc'].replace('Z','+00:00'))).total_seconds()/60
   if gap<0:overlap.append((a['flight_instance_id'],b['flight_instance_id']))
   if a['destination_airport']!=b['origin_airport']:position.append((a['flight_instance_id'],b['flight_instance_id']))
   if gap<45:turns.append((a['flight_instance_id'],b['flight_instance_id'],gap))
 ck('no_tail_overlap',not overlap,overlap);ck('physical_station_continuity',not position,position);ck('turn45',not turns,turns)
 ck('u8_in_reference_direct_design',all(d['block_minutes']<=480 for d in days),{'max_minutes':max(d['block_minutes'] for d in days)})
 stress=[]
 for mult in [0.9,1,1.2]:
  for turn in [30,45,60]:
   for mod,mp in module_maps.items():
    blocks=[sum(sum(BM[e]) for e in es)*mult for es in mp.values()]
    elapsed=[sum(sum(BM[e]) for e in es)*mult+(2*len(es)-1)*turn for es in mp.values()]
    stress.append({'module':mod,'block_multiplier':mult,'turn_min':turn,'max_daily_block_minutes':round(max(blocks),2),'max_daily_elapsed_minutes':round(max(elapsed),2),
      'u8_exceeded':max(blocks)>480,'u10_exceeded':max(blocks)>600,'operational_admission':'UNKNOWN','assumption_ids':['P08-SVX-A01','P08-SVX-A02','P08-SVX-A03']})
 writec('resource_sensitivity.csv',stress)
 ck('each_month_all_delivery_branches',len(monthly)==24*len(programmes)*4,len(monthly))
 ck('required_legacy_covered',len(actions)==17,list(actions),'родословная/статус,неэкономическийвердикт')
 ck('all_source_files_exact_pinned',all(x['commit'] in PINS.values() for x in INPUTS),len(INPUTS),'происхождениелокальныхвходов')
 ck('no_economic_result_invented',all(p['profit'] is None and p['passengers'] is None and p['market_share'] is None for p in programmes),'profit/passengers/share=null','границадоказательств')
 writej('checks.json',{'status':'PASS' if all(x['pass'] for x in checks) else 'FAIL','checks':checks,
   'not_run':['P05calibration','P06realRWbundle','independentacceptanceP06','crew/MRO/airportadmission','actualfleetavailability','fullcost/cash','wholecasefinalacceptance']})
 writej('p06_binding_map.json',{'contract_version':contract['version'],'contract_pin':PINS['P06'],'state':'NOT_READY_INPUT_ACCEPTANCE_PENDING',
  'proposed_owner_map':{'flights/assignments':'P03 принимаетdated_templatesиразделяетactualtype;crewid/nullнепропускать','markets/calendar/products/contracts/choice/response':'P05;всепоездкиисвоиепродажиодинраз','events/cash/openingbalances/coverage':'P04CD01–17сactualfutureadmission','versionedP/KEEPbundle':'координаторP08+P06;source_pins.json'},
  'no_toy_values_copied':True,'context_required':contract['context_required'],'bundle_required':contract['bundle_required'],
  'calendar_nulls':'Не заменятьunknown_monthsнаzero_months. Несгенерированныеднинефактотмены/отсутствияспроса.',
  'flight_ids':'идентификаторыэтогопакетавпредлагаемомсценарии;принятиеproducerперепроверяетuniqueness/physicalcapacity;WZcodeshareнеещёодинхвост'})
 writej('handoff.json',{'package':'P08-SVX-A','stage_A':'COMPLETE_RESEARCH_DESIGN_WITH_EXPLICIT_OPEN_GATES','stage_B':'NOT_RUN_P05_P06_PENDING','write_boundary':str(ROOT.relative_to(REPO)),
  'input_pins':PINS,'candidates':len(candidates),'programmes':len(programmes),'historical_chain_controls':len(controls),'legacy_dispositions':len(actions),'new_hypotheses':3,
  'critical_findings':['SVXSGC/RGK/MMKужеRWпопрямымпервичнымстраницам;сохранятьвKEEP','U12даёт8airportpairsпри2рабочих+Rpolicy;U12311при3+Rpolicy;нефактRWпарка','U1core4пары—промежуточнаяступень','ретаймингитреугольникиоцениваютсяпротивсохранённыхсвоихпродаж','денег/спросаненазначено;StageBчерезобщийP05/P06'],
  'required_next':specs,'checks_file':'checks.json','manifest_file':'manifest.json'})
 print(jd({'candidates':len(candidates),'programmes':len(programmes),'flights':len(flights),'rotations':len(rotations),'checks':all(x['pass'] for x in checks),'module_bh':module_bh,'control_u8_exceed':[r['control_id'] for r in control_sum if r['daily_u8_exceeded']]}))

if __name__=='__main__':main()
