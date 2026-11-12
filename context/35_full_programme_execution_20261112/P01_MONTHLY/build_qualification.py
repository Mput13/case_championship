#!/usr/bin/env python3
import csv,json,pathlib,hashlib,datetime
P=pathlib.Path(__file__).resolve().parent
pin='d9486f113f074c185a94bcc5c0afeef12ea3574f'
def write(name,rows,fields=None):
 with (P/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
rows=[]
f=P/'inputs/BASE_known_flows.csv';lines=f.read_text().splitlines()
for i,r in enumerate(csv.DictReader(lines),2):
 orig=r.copy();pair=r['from_iata']+'-'+r['to_iata'];kind='airport_pair_segment';status='SECONDARY_INHERITED_NOT_REVALIDATED';eligible='УСЛОВНО: контроль масштаба перевезённых сегментов за исходный период';bad='Конечные OD, месячная сезонность, цены, загрузка и общий потенциальный спрос не наблюдаются'
 if r['period']!='2025':
  eligible='УСЛОВНО: сегменты только I полугодия 2025; исходный annual_factor=2 не применять';bad+='; удвоение полугодия не даёт наблюдённый год'
 if r['coverage']=='region':
  kind='region_to_city_segment';eligible='НЕТ для CEK: совокупность всей Челябинской области не разделена между CEK и MQF';bad+='; нельзя приписать все 1,1 млн аэропорту CEK'
 if r['coverage']=='airline_group':
  kind='carrier_group_airport_pair_segment_subset';eligible='УСЛОВНО: нижняя граница всех перевезённых сегментов пары только после сверки направлений/аэропортов; не нижняя граница конечных OD';status='CARRIER_MIRROR_INHERITED_NOT_REVALIDATED'
 if pair=='KUF-MRV':status='INTERNAL_SOURCE_WITHOUT_PRIMARY_URL';eligible='НЕТ до получения первоисточника, периода и определения 47 тыс.'
 qual='APPROX' if r['from_iata'] in ['AER','CEK'] or (r['from_iata']=='KJA') else 'REPORTED_INTEGER'
 if pair=='BAX-MOW':qual='GT'
 if pair=='BAX-LED':qual='NEAR_BELOW_UNQUANTIFIED'
 rows.append(dict(observation_id=f'KF{i-1:03d}',source_row_id=f'BASE_known_flows.csv:{i}',source_row_sha256=hashlib.sha256(lines[i-1].encode()).hexdigest(),source_file_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),source_commit=pin,source_path='context/35_full_programme_execution_20261112/P02/inputs/BASE_known_flows.csv',from_iata=r['from_iata'],to_iata=r['to_iata'],value=r['pax'],value_qualifier=qual,unit='пассажирские сегменты; точное определение требует первоисточника',period_start='2025-01-01',period_end='2025-06-30' if r['period']!='2025' else '2025-12-31',period_original=r['period'],annual_factor_original=r['annual_factor'],annual_factor_applied='',granularity=kind,direction_basis='UNKNOWN; не делить на 2',moscow_airport_basis='MOW: аэропорты не разделены' if r['to_iata']=='MOW' else 'не применимо',source_status=status,source_url=r['source'],organization='СМИ со ссылкой на аэропорт' if r['coverage']!='airline_group' else 'Группа Аэрофлот; копия сообщения в Samokatus',publication_date='UNKNOWN',calibration_eligibility=eligible,endpoint_od_eligible='НЕТ',monthly_seasonality_eligible='НЕТ',prohibited_use=bad,assumption_ids='PM-A01;PM-A02;PM-A03',quote=r['quote']))
write('calibration_eligibility.csv',rows)
write('endpoint_od_observations.csv',[],['observation_id','origin_airport','destination_airport','period_start','period_end','value','unit','direction_basis','journey_definition','carrier_coverage','source_id','source_row_id','source_sha256','assumption_ids'])
cross=[
 ('airport_total','Аэропорт × месяц','Обслуженные пассажиры; число событий обслуживания','Контроль масштаба и наблюдённого сезонного профиля аэропорта','Нельзя распределять между парами без модели/данных; arrivals+departures и прямой транзит уточняются','PM-A01'),
 ('airport_pair_segment','Аэропорт × пункт маршрута × период','Перевезённые на плече пассажиры, включая трансферных','Контроль сегментов при совпадении периода, направления и совокупности','Не конечные OD; MOW не аэропорт; два направления нельзя удвоить повторно','PM-A02'),
 ('carrier_month','Перевозчик/группа × месяц','Перевезённые пассажиры по сети','Контроль масштаба и сезонности соответствующей сети','Не сезонность отдельного маршрута; группа содержит компании; вертолёты отдельно','PM-A04'),
 ('endpoint_od','Начальный и конечный аэропорты поездки × период','Конечные поездки; сквозной маршрут начисляется один раз','Прямая калибровка P05 при совместимой границе','В пакете на первом транше подтверждённых строк нет','PM-A01'),
 ('tourism_emiss62073','Регион × месяц','Размещённые лица в КСР по определению ЕМИСС','Внешняя объясняющая переменная туризма','18 360 значений не авиационные OD; нет автоматического коэффициента перевода в авиапассажиров','PM-A05'),
 ('published_schedule','Рейс × дата × плечо','Опубликованное предложение','Календарь предложения после физической привязки рейсов','Не факт продаж, выполнения, загрузки или свободный ресурс RW','PM-A06'),
 ('cumulative_difference','Одна и та же совокупность × последовательные накопленные периоды','Месяц = YTD(t) - YTD(t-1)','Только при одинаковом определении и покрытии; хранить оба источника и точность','Несмежные периоды дают блок, не один месяц; округление не исчезает; не вычитать пересмотренные несовместимые серии','PM-A07')]
write('granularity_crosswalk.csv',[dict(granularity=a,grain=b,numerator=c,eligible_use=d,limitations=e,assumption_ids=f) for a,b,c,d,e,f in cross])
ass=[
 ('PM-A01','Не считать аэропортовые пассажирособытия конечными поездками','Исследователь P01; определения источников','UNKNOWN: доля трансфера/прямого транзита','При ошибочной конверсии искажаются OD и доли; уточнить форму статнаблюдения и продажи','Не применять конверсию без данных'),
 ('PM-A02','Не делить поток пары на 2 без явного направления','Исследователь P01; источник может считать вылеты или оба направления','UNKNOWN: направленность каждой непроверенной строки','Ошибка до множителя 2; сверить оригинальный отчёт и аэропорты Москвы','Отдельные ветви направлений только после проверки'),
 ('PM-A03','Не удваивать I полугодие OVB до полного года','Исследователь P01; сезонность неизвестна','UNKNOWN: доля I полугодия в году для пары','Ошибка годового масштаба; получить II полугодие и полный календарный год','Использовать 2025-01-01..2025-06-30'),
 ('PM-A04','Отделять fixed-wing от вертолётов и группу от авиакомпании','Исследователь P01; публикации ЮТэйр/Росавиации','UNKNOWN: состав групп по месяцам до сверки','Смешение завышает сравнимый масштаб; проверить юрлица и тип операций','Сохранять состав и единицу каждой публикации'),
 ('PM-A05','Профиль размещений ЕМИСС не переводить автоматически в авиацию','Исследователь P01; разные совокупности','UNKNOWN: коэффициент размещения → авиапоездка','Искажение сезонности/спроса; валидация на фактических рядах аэропортов и пар','Оставить внешним фактором P05'),
 ('PM-A06','Не выдавать P02/P03 за фактические кресла/годовую сеть','Задание координатора; P02v2/P03v2','UNKNOWN: выполнение/продажи/crew/ТО/KEEP','Невозможно считать наблюдённую загрузку; запросить фактическое исполнение','Только опубликованное предложение с физической привязкой'),
 ('PM-A07','Разность YTD допустима только для соседних совместимых периодов','Исследователь P01; арифметическая трансформация','Точность исходных публикаций сохраняется; диапазон ревизий UNKNOWN','Округления накапливаются; сверить прямой месячный отчёт и исходные версии','Не интерполировать пропуски')]
write('assumptions.csv',[dict(assumption_id=a,assumption=b,owner_reason=c,range_or_unknown=d,impact_and_how_to_refine=e,application=f) for a,b,c,d,e,f in ass])
summary={'tranche':'qualification_v1','as_of_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'known_flows_qualified':len(rows),'endpoint_od_confirmed_rows':0,'partial_year_rows':4,'regional_rows':1,'carrier_subset_rows':6,'economic_rejection':False,'files':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [P/'calibration_eligibility.csv',P/'granularity_crosswalk.csv',P/'endpoint_od_observations.csv',P/'assumptions.csv',P/'input_manifest.json']}}
(P/'usable_tranche_01.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False))
