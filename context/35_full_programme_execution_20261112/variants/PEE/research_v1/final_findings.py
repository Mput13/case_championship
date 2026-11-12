from pathlib import Path
import csv,json,subprocess,hashlib,io
B=Path(__file__).resolve().parent

def read(p):return list(csv.DictReader((B/p).open()))
def save(p,x):(B/p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def table(p,rs):
 with (B/p).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
issues=[]
for r in read('inputs/P02_competitor_products.csv'):
 if r['origin']=='PEE' and r['destination']=='KUF' and r['departure_local']=='20:00':
  issues.append(dict(issue_id='PEE-CLOCK-KUF-'+r['product_id'],product_id=r['product_id'],source_row=r['_source_row'],row_sha256=r['_row_sha256'],source_commit='d9486f113f074c185a94bcc5c0afeef12ea3574f',source_path='context/35_full_programme_execution_20261112/P02/competitor_products.csv',source_url=r['source_url'],source_id=r['source_id'],flight=r['flight'],period=r['period'],unit='local clock; minute elapsed',coverage='Одно правило/его повторный source export; не доказательство отмены рейса',reported_departure_local='20:00 PEE UTC+5',reported_arrival_local='17:00 KUF UTC+4',same_day_elapsed_minutes=-120,status='NOT_ADMITTED_NEEDS_SOURCE_DAY_OFFSET_OR_CLOCK_CORRECTION',correction='UNKNOWN; произвольный перенос даты не выбран',next_owner='P02; CR08'))
save('local_data_issues.json',dict(issues=issues,scope='Локальная проверка пригодности; общий P02 не изменён.'))
audit=[]
for s,p in [('d9486f113f074c185a94bcc5c0afeef12ea3574f','context/35_full_programme_execution_20261112/P02/clock_conflicts.csv'),('79dc698b99dfe866886d32376ed388e85bdd039c','context/35_full_programme_execution_20261112/P03/existing_commitments.csv')]:
 raw=subprocess.check_output(['git','show',s+':'+p]);rs=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))));matches=[i for i,r in enumerate(rs,2) if any('PEE' in str(v) or 'Перм' in str(v) for v in r.values())]
 audit.append(dict(commit=s,path=p,git_blob=subprocess.check_output(['git','rev-parse',s+':'+p],text=True).strip(),source_sha256=hashlib.sha256(raw).hexdigest(),source_rows=len(rs),selected_rows=matches,selection='PEE или Перм в любом поле',scope='Отсутствие выбранной строки означает только отсутствие в этом файле; не отсутствие обязательств или ошибок в действительности.'))
save('selection_audit.json',audit)
e=[r for r in read('evidence.csv') if r['evidence_id']!='E27']
for r in e:
 if r['evidence_id']=='E09':r.update(value='17475; daily_on_2026-05-06',unit='обслуженный пассажир/квартал; рейс/сутки',coverage='17 475 пассажиров S7 за I квартал; ежедневная PEE–OVB на дату сообщения. Зимний календарь и конечные OD неизвестны.')
 if r['evidence_id']=='E25':r['coverage']='13 partial; 52 uncovered; 0 comparable quotes. Source export не admission кресел; selection_audit.json и local_data_issues.json разделяют общее покрытие и локальный дефект.'
e.append(dict(e[0],evidence_id='E27',claim='Отрицательное same-day elapsed в правиле PEE–KUF',value='-120',unit='минут при UTC+5/UTC+4',period='правило среды 28.10–30.12.2026',granularity='product rule; исходные строки в local_data_issues.json',source_id='PIN-P02',coverage='PEE 20:00 → KUF 17:00; день прибытия/исправление UNKNOWN. Не допускать как физический вылет.',status='LOCAL_DATA_QUALITY_FINDING',assumption_id=''))
table('evidence.csv',e)
src=[r for r in read('sources.csv') if r['source_id']!='RESEARCH_DESIGN']
src.append(dict(src[0],source_id='RESEARCH_DESIGN',url='local:programme_candidates.json;assumptions.csv;resource_screen.json',organization='Исследователь PEE / Sol 6.1 xhigh',published_at='2026-11-12',retrieved_at='2026-11-12',period='Проект 2027–2028; номинальный экран 08–14.05.2028',unit='сценарный параметр; не наблюдение',granularity='Локальная конструкция опыта',status='EXPLICIT_RESEARCH_DESIGN',coverage='Параметры с обоснованием и UNKNOWN границами; не прогноз и не доверительный интервал.',source_pin='THIS_PACKAGE',locator='assumptions.csv'))
for r in src:
 if r['source_id']=='N11_AIRPORT_HOME':r['coverage']='HTTP 200, содержательный текст не получен; точная причина UNKNOWN. Текущие тарифы не извлечены.'
table('sources.csv',src)
print('Pinned row checks: 2 clock issue exports; no automatic correction.')
# Сохраняем только применимые общие неизвестные drivers, не чужие аэропортовые rates.
pins=json.loads((B/'source_pins.json').read_text())
for name,predicate,description in [
 ('P04_cost_ranges.csv',lambda r:r['geography_or_airport']=='airport_or_base_or_route_required' and r['aircraft_type'] not in ['Tu214','other_existing_RW_type'],'Общие неизвестные драйверы, применимые PEE SSJ/SJ и generic; исключены rates других аэропортов, старые прокси и другие типы.'),
 ('P04_thresholds.csv',lambda r:r['threshold_id'] in ['TH-FIXED','TH-LAUNCH','TH-MRO','TH-SUPPORT'],'Только четыре используемых условных порога P04.')]:
 m=next(r for r in pins if r['output']=='inputs/'+name);raw=subprocess.check_output(['git','show',m['commit']+':'+m['path']]);original=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))));out=io.StringIO();w=csv.DictWriter(out,fieldnames=list(original[0])+['_source_row','_row_sha256']);w.writeheader()
 for i,r in enumerate(original,2):
  if predicate(r):w.writerow(dict(r,_source_row=i,_row_sha256=hashlib.sha256(json.dumps(r,sort_keys=True,ensure_ascii=False).encode()).hexdigest()))
 (B/m['output']).write_text(out.getvalue());m['output_sha256']=hashlib.sha256(out.getvalue().encode()).hexdigest();m['selection']=description
save('source_pins.json',pins)
# Краткие постановки в самой таблице, чтобы её можно было передать общим владельцам.
questions={
'CR01':('VOG: внешняя ротация, местная база или прибавка из SVX?','P03: готовый tail/донор и UTC block. P05: месячный PEE/SVX–VOG OD и fares. P04: ставки, право на поддержку и cash.','Точные даты 44 пар при полном сезоне; полный added result, lost own sales, денежный разрыв и пороги поддержки/запуска.'),
'CR02':('Один борт: радиальная PEE или лучшее применение в SVX?','Общий календарь; полная цена базы/crew/MRO; OD LED/VOG/NOZ/KJA; международный KEEP и ресурс альтернативы.','Помесячный ресурс и простой, собственный переток, funding и условия остановки; общий target 8–12 пар.'),
'CR03':('Что добавляет синхронизация тех же рейсов?','Два борта того же ready calendar; MCT/багаж/DCS/recovery; P05 конечные LED–NOZ и VOG–KJA, обратные поездки и конкуренты.','Разделить поездки и сегменты, сохранить кресла, проверить время/crew/MRO и стоимость защиты пересадки.'),
'CR04':('Есть ли ниша прямого из MCX или LED; как проверить MRV из C15?','Даты и частоты конкурентов; сопоставимые билеты с багажом/сборами и lead 7/30/90; ресурс исходной базы; платный OD.','Полная цена и время, новые и перенесённые свои продажи, короткая поездка и поездка на 3/4 ночи.'),
'CR05':('Ноль новых самолётов: полезен ли подвоз или партнёрский продукт?','Датированные автобус/поезд и рейс SVX, residence, договор защиты, открытые физические кресла.','Полная цена/время/багаж/риск без виртуальных новых мест; собственный переток и порог цены договора.'),
'CR06':('Теряет ли внутренний проект международный KEEP или лучшее использование нового борта?','Продления MSQ/BUS 2027–2028, права/слоты/ресурс; общий P05 OD и net fare; ветвь 0 новых Ту-214.','Единая дельта всего затронутого бизнеса; не сумма независимых прибылей.'),
'CR07':('Корпоративная ниша: новый рейс или блок действующих мест?','Конкретные дата/пункт/плательщик платной поездки; договор блока и release, существующий продукт и общий OD.','После допуска предложения — порог оплаченных мест/контрактной суммы в P04/P06. До этого частота UNKNOWN.'),
'CR08':('Закрыть локальные пробелы конкуренции и физических продуктов.','13 partial / 52 uncovered; оператор GOJ; московские аэропорты отдельно; clock issue PEE–KUF; throughstop/continuity и dated baggage/fare.','Исходные записи и принятые physical legs с binding IDs; неизвестных конкурентов не обнулять.'),
'CR09':('Подтвердить локальную эксплуатацию PEE отдельно по типам.','AIP/NOTAM, стоянки/пики/ночь, акт ввода перрона, SGHA, SaM146/ПД-8 scope, crew, spares/MRO/reserve, KEEP и MCT.','Каждое назначение по датам проходит проверку либо получает точный gap; локальные ставки, договоры и обязательства выхода.'),
'CR10':('Отдельные непроверенные ветви не считать отказами.','MMK/OMS/RGK/GOJ/IKT/NQZ/KVK: общий конечный OD, сезон и конкуренты; payload/range IKT; точный support calendar и владение общими OD.','Объяснимый отдельный исход каждой пары. NOT_RUN остаётся незавершённой Stage B работой, не ранним экономическим отсевом.')}
req=read('comparison_requests.csv')
for r in req:
 r['question'],r['needed_inputs'],r['required_outputs']=questions[r['request_id']]
 r['blocks']='Операционный/денежный выбор Stage B' if r['request_id']!='CR10' else 'Дополнительный поиск; не препятствует передаче завершённого локального Stage A.'
table('comparison_requests.csv',req)
